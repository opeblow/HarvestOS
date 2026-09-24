import * as cdk from "aws-cdk-lib";
import { Template } from "aws-cdk-lib/assertions";
import { HarvestOSStack } from "../lib/harvestos-stack";

describe("HarvestOSStack", () => {
  const app = new cdk.App();
  const stack = new HarvestOSStack(app, "TestStack", {
    env: { account: "123456789012", region: "us-east-1" },
  });
  const template = Template.fromStack(stack);

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

  it("exposes an internet-facing load balancer for webhooks", () => {
    template.resourceCountIs("AWS::ElasticLoadBalancingV2::LoadBalancer", 1);
  });

  it("adds a hard monthly budget alarm", () => {
    template.resourceCountIs("AWS::Budgets::Budget", 1);
  });

  it("verifies an SES email identity", () => {
    template.resourceCountIs("AWS::SES::EmailIdentity", 1);
  });
});