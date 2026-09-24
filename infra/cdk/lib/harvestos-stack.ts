import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import { Compute } from "./compute";
import { Observability } from "./observability";
import { Storage } from "./storage";

export interface HarvestOSStackProps extends cdk.StackProps {
  /** Kebab-case name used for resource names (defaults to stackName slug). */
  serviceName?: string;
  /** Create the optional S3 asset bucket (defaults to HARVESTOS_ENABLE_ASSET_BUCKET). */
  enableAssetBucket?: boolean;
  /** Create the optional SES sending identity + grants (defaults to HARVESTOS_ENABLE_EMAIL). */
  enableEmail?: boolean;
  /** SES identity to verify when email is enabled. */
  sesIdentity?: string;
  /** From address used when email is enabled. */
  sesFromAddress?: string;
}

function envFlag(value: string | undefined, fallback = false): boolean {
  if (value === undefined) return fallback;
  return ["1", "true", "yes", "on"].includes(value.toLowerCase());
}

/**
 * HarvestOS — everything a stranger needs to stand the platform up, defined
 * as code. Core storage (DynamoDB + KMS), compute (Fargate + ALB), and
 * observability (dashboard + budget alarm) are always provisioned. S3 asset
 * storage and the SES email identity are optional adapters, off by default,
 * because the product runs fully on the in-app notification inbox.
 */
export class HarvestOSStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: HarvestOSStackProps = {}) {
    super(scope, id, props);

    const region =
      this.region ??
      (process.env.AWS_DEFAULT_REGION ?? "us-east-1");
    const account =
      this.account ?? (process.env.AWS_ACCOUNT_ID ?? "000000000000");

    const enableAssetBucket =
      props.enableAssetBucket ?? envFlag(process.env.HARVESTOS_ENABLE_ASSET_BUCKET);
    const enableEmail = props.enableEmail ?? envFlag(process.env.HARVESTOS_ENABLE_EMAIL);
    const sesFromAddress =
      props.sesFromAddress ?? process.env.SES_FROM_ADDRESS ?? "harvestos@example.com";
    const sesIdentity =
      props.sesIdentity ?? process.env.SES_IDENTITY ?? sesFromAddress;

    const storage = new Storage(this, "Storage", {
      tableName: "harvestos-sessions",
      assetBucketName: `harvestos-assets-${account}-${region}`,
      enableAssetBucket,
    });

    new Compute(this, "Compute", {
      storage,
      region,
      sesFromAddress,
      enableEmail,
    });

    new Observability(this, "Observability", {
      storage,
      region,
      sesIdentity,
      enableEmail,
      monthlyBudgetUsd: Number(process.env.HARVESTOS_MONTHLY_BUDGET_USD ?? 300),
      alarmEmail: process.env.BUDGET_ALARM_EMAIL ?? "budget@example.com",
    });
  }
}
