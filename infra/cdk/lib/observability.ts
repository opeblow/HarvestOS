import * as cdk from "aws-cdk-lib";
import * as budgets from "aws-cdk-lib/aws-budgets";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as ses from "aws-cdk-lib/aws-ses";
import { Construct } from "constructs";
import { Storage } from "./storage";

export interface ObservabilityProps {
  storage: Storage;
  region: string;
  /** SES identity to verify for sending (email or domain). */
  sesIdentity: string;
  /** Email (SES) is an optional adapter; the identity is created only when enabled. */
  enableEmail: boolean;
  /** Monthly cost ceiling in USD. */
  monthlyBudgetUsd: number;
  alarmEmail: string;
}

/**
 * Optional SES sending identity, a CloudWatch dashboard (traffic per channel
 * would be populated by the backend's structured logs), and a hard budget
 * alarm. The dashboard and budget alarm are core and always created.
 */
export class Observability extends Construct {
  constructor(scope: Construct, id: string, props: ObservabilityProps) {
    super(scope, id);

    if (props.enableEmail) {
      new ses.EmailIdentity(this, "SesIdentity", {
        identity: { value: props.sesIdentity },
      });
    }

    const dashboard = new cloudwatch.Dashboard(this, "Dashboard", {
      dashboardName: "HarvestOS",
    });

    const messages = new cloudwatch.Metric({
      namespace: "HarvestOS",
      metricName: "messages",
      dimensionsMap: {},
    });

    dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: "# HarvestOS — operational view",
        width: 24,
        height: 1,
      }),
      new cloudwatch.GraphWidget({
        title: "Messages routed (custom)", 
        left: [messages],
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: "Sessions table traffic",
        left: [
          this._tableMetric(props.storage, "ConsumedReadCapacityUnits", "Read"),
          this._tableMetric(props.storage, "ConsumedWriteCapacityUnits", "Write"),
        ],
        width: 12,
      }),
    );

    new budgets.CfnBudget(this, "BudgetAlarm", {
      budget: {
        budgetName: "HarvestOS-Monthly-Cap",
        budgetType: "COST",
        timeUnit: "MONTHLY",
        budgetLimit: {
          amount: props.monthlyBudgetUsd,
          unit: "USD",
        },
        costTypes: { includeTax: true, includeSubscription: true },
      },
      notificationsWithSubscribers: [
        {
          notification: {
            notificationType: "ACTUAL",
            comparisonOperator: "GREATER_THAN",
            threshold: 80,
            thresholdType: "PERCENTAGE",
          },
          subscribers: [{ subscriptionType: "EMAIL", address: props.alarmEmail }],
        },
        {
          notification: {
            notificationType: "FORECASTED",
            comparisonOperator: "GREATER_THAN",
            threshold: 100,
            thresholdType: "PERCENTAGE",
          },
          subscribers: [{ subscriptionType: "EMAIL", address: props.alarmEmail }],
        },
      ],
    });
  }

  private _tableMetric(
    storage: Storage,
    metricName: string,
    label: string,
  ): cloudwatch.Metric {
    return new cloudwatch.Metric({
      namespace: "AWS/DynamoDB",
      metricName,
      label,
      dimensionsMap: { TableName: storage.table.tableName },
      statistic: "Sum",
      period: cdk.Duration.minutes(5),
    });
  }
}