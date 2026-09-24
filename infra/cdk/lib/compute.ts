import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as path from "path";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";
import { Storage } from "./storage";

export interface ComputeProps {
  storage: Storage;
  region: string;
  sesFromAddress: string;
}

/**
 * ECS Fargate service running the FastAPI backend behind an ALB. Inbound
 * webhooks (SMS / WhatsApp / SES) and the read-only dashboard API all land
 * here; there is no separate lambda per channel for the MVP.
 */
export class Compute extends Construct {
  readonly loadBalancer: elbv2.ApplicationLoadBalancer;
  readonly service: ecs.FargateService;
  readonly listener: elbv2.ApplicationListener;

  constructor(scope: Construct, id: string, props: ComputeProps) {
    super(scope, id);

    const vpc = new ec2.Vpc(this, "Vpc", {
      maxAzs: 2,
      natGateways: 1,
      restrictDefaultSecurityGroup: true,
    });

    const cluster = new ecs.Cluster(this, "Cluster", { vpc });

    const taskDefinition = new ecs.FargateTaskDefinition(this, "FastApiTask", {
      cpu: 512,
      memoryLimitMiB: 1024,
    });

    props.storage.table.grantReadWriteData(taskDefinition.taskRole);
    props.storage.assetBucket.grantReadWrite(taskDefinition.taskRole);
    taskDefinition.addToTaskRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: ["ses:SendEmail", "ses:SendRawEmail", "sesv2:SendEmail"],
        resources: [
          `arn:aws:ses:${props.region}:${cdk.Stack.of(this).account}:identity/${props.sesFromAddress}`,
        ],
      }),
    );
    if (process.env.HARVESTOS_AGENT_BACKEND === "bedrock") {
      taskDefinition.addToTaskRolePolicy(
        new cdk.aws_iam.PolicyStatement({
          actions: ["bedrock:InvokeModel"],
          resources: [
            `arn:aws:bedrock:${props.region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2`,
          ],
        }),
      );
    }

    const image = ecs.ContainerImage.fromAsset(path.join(__dirname, "..", "..", "..", "backend"), {
      file: "Dockerfile",
    });

    const container = taskDefinition.addContainer("Web", {
      image,
      memoryLimitMiB: 1024,
      logging: ecs.LogDrivers.awsLogs({ streamPrefix: "harvestos-web" }),
      environment: {
        APP_ENV: "prod",
        STORAGE: "aws",
        AGENT_BACKEND: process.env.HARVESTOS_AGENT_BACKEND ?? "rule",
        AWS_DEFAULT_REGION: props.region,
        TABLE_NAME: props.storage.table.tableName,
        ASSET_BUCKET: props.storage.assetBucket.bucketName,
        SES_FROM_ADDRESS: props.sesFromAddress,
        SENTRY_DSN: process.env.SENTRY_DSN ?? "",
        PAYSTACK_SECRET_KEY: process.env.PAYSTACK_SECRET_KEY ?? "",
        PAYSTACK_PUBLIC_KEY: process.env.PAYSTACK_PUBLIC_KEY ?? "",
        SMS_ORIGINATION_IDENTITY: process.env.SMS_ORIGINATION_IDENTITY ?? "",
        WHATSAPP_LINKED_ACCOUNT_ID: process.env.WHATSAPP_LINKED_ACCOUNT_ID ?? "",
        WHATSAPP_PHONE_NUMBER_ID: process.env.WHATSAPP_PHONE_NUMBER_ID ?? "",
      },
    });
    const authSecretArn = process.env.HARVESTOS_AUTH_SECRET_ARN;
    if (authSecretArn) {
      const authSecret = secretsmanager.Secret.fromSecretCompleteArn(
        this,
        "DashboardAuthSecret",
        authSecretArn,
      );
      container.addSecret(
        "HARVESTOS_SESSION_SECRET",
        ecs.Secret.fromSecretsManager(authSecret, "session_secret"),
      );
    }
    container.addPortMappings({ containerPort: 8000 });

    this.service = new ecs.FargateService(this, "FastApiService", {
      cluster,
      taskDefinition,
      desiredCount: 1,
      capacityProviderStrategies: [
        { capacityProvider: "FARGATE", weight: 1 },
      ],
    });

    this.loadBalancer = new elbv2.ApplicationLoadBalancer(this, "Alb", {
      vpc,
      internetFacing: true,
    });
    this.listener = this.loadBalancer.addListener("Http", {
      port: 80,
    });

    this.listener.addTargets("WebTargets", {
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [this.service],
      healthCheck: {
        path: "/healthz",
        healthyHttpCodes: "200,302",
        interval: cdk.Duration.seconds(30),
      },
    });

    new cdk.aws_cloudwatch.Alarm(this, "Alb5xxAlarm", {
      metric: this.loadBalancer.metrics.httpCodeElb(elbv2.HttpCodeElb.ELB_5XX_COUNT),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator:
        cdk.aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
    });

    new cdk.CfnOutput(this, "ServiceUrl", {
      value: `http://${this.loadBalancer.loadBalancerDnsName}`,
      description:
        "HTTP demo endpoint only. Add an HTTPS listener and certificate before production use.",
    });
  }
}
