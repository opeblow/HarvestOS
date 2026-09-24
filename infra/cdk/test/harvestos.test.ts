import * as cdk from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { HarvestOSStack, HarvestOSStackProps } from "../lib/harvestos-stack";

function build(props: Partial<HarvestOSStackProps> = {}): Template {
  const app = new cdk.App();
  const stack = new HarvestOSStack(app, "TestStack", {
    env: { account: "123456789012", region: "us-east-1" },
    ...props,
  });
  return Template.fromStack(stack);
}

describe("HarvestOSStack (core defaults)", () => {
  const template = build();

  it("creates the DynamoDB session table", () => {
    template.resourceCountIs("AWS::DynamoDB::Table", 1);
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      TableName: "harvestos-sessions",
      TimeToLiveSpecification: { AttributeName: "ttl", Enabled: true },
    });
  });

  it("encrypts storage with a customer-managed KMS key", () => {
    template.resourceCountIs("AWS::KMS::Key", 1);
  });

  it("does not create an S3 asset bucket unless enabled", () => {
    template.resourceCountIs("AWS::S3::Bucket", 0);
  });

  it("does not create an SES identity unless enabled", () => {
    template.resourceCountIs("AWS::SES::EmailIdentity", 0);
  });

  it("exposes an internet-facing load balancer for webhooks", () => {
    template.resourceCountIs("AWS::ElasticLoadBalancingV2::LoadBalancer", 1);
  });

  it("adds a hard monthly budget alarm", () => {
    template.resourceCountIs("AWS::Budgets::Budget", 1);
  });

  it("runs the core app with in-app notifications and optional channels disabled", () => {
    template.hasResourceProperties(
      "AWS::ECS::TaskDefinition",
      Match.objectLike({
        ContainerDefinitions: Match.arrayWith([
          Match.objectLike({
            Environment: Match.arrayWith([
              { Name: "NOTIFICATION_PROVIDER", Value: "in_app" },
              { Name: "EMAIL_PROVIDER", Value: "disabled" },
              { Name: "ASSET_STORAGE", Value: "local" },
            ]),
          }),
        ]),
      }),
    );
  });
});

describe("HarvestOSStack (optional adapters enabled)", () => {
  const template = build({ enableAssetBucket: true, enableEmail: true });

  it("creates an encrypted, private S3 bucket", () => {
    template.hasResourceProperties("AWS::S3::Bucket", {
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      },
    });
  });

  it("verifies an SES email identity", () => {
    template.resourceCountIs("AWS::SES::EmailIdentity", 1);
  });

  it("wires the email and S3 adapters into the container", () => {
    template.hasResourceProperties(
      "AWS::ECS::TaskDefinition",
      Match.objectLike({
        ContainerDefinitions: Match.arrayWith([
          Match.objectLike({
            Environment: Match.arrayWith([
              { Name: "EMAIL_PROVIDER", Value: "ses" },
              { Name: "ASSET_STORAGE", Value: "s3" },
            ]),
          }),
        ]),
      }),
    );
  });
});
