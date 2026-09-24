import * as cdk from "aws-cdk-lib";
import { HarvestOSStack } from "../lib/harvestos-stack";

const app = new cdk.App();

new HarvestOSStack(app, "HarvestOSStack", {
  stackName: "HarvestOS",
  description:
    "HarvestOS — agentic commerce layer for smallholder farmers (AWS CDS Agentic AI Hackathon)",
  env: {
    account:
      process.env.AWS_ACCOUNT_ID ??
      process.env.CDK_DEFAULT_ACCOUNT,
    region:
      process.env.AWS_DEFAULT_REGION ??
      process.env.CDK_DEFAULT_REGION ??
      "us-east-1",
  },
});

app.synth();