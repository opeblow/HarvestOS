import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as kms from "aws-cdk-lib/aws-kms";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";

export interface StorageProps {
  tableName: string;
  assetBucketName: string;
  /** S3 is an optional adapter; the core app runs with local asset storage. */
  enableAssetBucket?: boolean;
}

/**
 * Single-table DynamoDB design keyed by `phoneNumber` (identity) + `sk`
 * (session/message sub-keys). This is the core session store and is always
 * provisioned. The S3 asset bucket for photos and generated PDFs is optional
 * and only created when explicitly enabled.
 */
export class Storage extends Construct {
  readonly table: dynamodb.Table;
  readonly assetBucket?: s3.Bucket;
  readonly key: kms.Key;

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id);

    this.key = new kms.Key(this, "DataKey", {
      description: "HarvestOS customer-managed key for sessions + assets",
      enableKeyRotation: true,
    });

    this.table = new dynamodb.Table(this, "SessionsTable", {
      tableName: props.tableName,
      partitionKey: {
        name: "pk",
        type: dynamodb.AttributeType.STRING, // fromNumber / phoneNumber
      },
      sortKey: { name: "sk", type: dynamodb.AttributeType.STRING }, // meta | msg:<id>
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.key,
      timeToLiveAttribute: "ttl",
      // Farmer and finance records must survive stack replacement/deletion.
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      pointInTimeRecovery: true,
    });

    this.table.addGlobalSecondaryIndex({
      indexName: "ByChannelTs",
      partitionKey: { name: "channel", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "ts", type: dynamodb.AttributeType.STRING },
    });
    this.table.addGlobalSecondaryIndex({
      indexName: "ByLoanStatus",
      partitionKey: { name: "loanStatus", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "updatedTs", type: dynamodb.AttributeType.STRING },
    });

    if (props.enableAssetBucket) {
      this.assetBucket = new s3.Bucket(this, "AssetsBucket", {
        bucketName: props.assetBucketName,
        encryption: s3.BucketEncryption.KMS,
        encryptionKey: this.key,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        enforceSSL: true,
        versioned: true,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
        lifecycleRules: [
          {
            id: "expire-assets",
            enabled: true,
            expiration: cdk.Duration.days(90),
          },
        ],
      });
    }
  }
}
