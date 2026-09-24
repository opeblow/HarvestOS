import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import { Compute } from "./compute";
import { Observability } from "./observability";
import { Storage } from "./storage";

export interface HarvestOSStackProps extends cdk.StackProps {
  /** Kebab-case name used for resource names (defaults to stackName slug). */
  serviceName?: string;
}

/**
 * HarvestOS — everything a stranger needs to stand the platform up, defined
 * as code. Storage (DynamoDB + S3 + KMS), compute (Fargate + ALB), and
 * observability (SES, dashboard, budget alarm).
 */
export class HarvestOSStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: HarvestOSStackProps = {}) {
    super(scope, id, props);

    const region =
      this.region ??
      (process.env.AWS_DEFAULT_REGION ?? "us-east-1");
    const account =
      this.account ?? (process.env.AWS_ACCOUNT_ID ?? "000000000000");

    const storage = new Storage(this, "Storage", {
      tableName: "harvestos-sessions",
      assetBucketName: `harvestos-assets-${account}-${region}`,
    });

    new Compute(this, "Compute", {
      storage,
      region,
      sesFromAddress: process.env.SES_FROM_ADDRESS ?? "harvestos@example.com",
    });

    new Observability(this, "Observability", {
      storage,
      region,
      sesIdentity: process.env.SES_IDENTITY ?? (process.env.SES_FROM_ADDRESS ?? "harvestos@example.com"),
      monthlyBudgetUsd: Number(process.env.HARVESTOS_MONTHLY_BUDGET_USD ?? 300),
      alarmEmail: process.env.BUDGET_ALARM_EMAIL ?? "budget@example.com",
    });
  }
}
