resource "aws_cloudwatch_dashboard" "api" {
  dashboard_name = "${local.name_prefix}-api-dashboard"

  dashboard_body = jsonencode(
    {
      widgets = [
        {
          type   = "metric"
          x      = 0
          y      = 0
          width  = 12
          height = 6

          properties = {
            title  = "Application Load Balancer Request Count"
            region = var.aws_region
            metrics = [
              [
                "AWS/ApplicationELB",
                "RequestCount",
                "LoadBalancer",
                aws_lb.api.arn_suffix
              ]
            ]
            stat   = "Sum"
            period = 300
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 0
          width  = 12
          height = 6

          properties = {
            title  = "Application Load Balancer Target Response Time"
            region = var.aws_region
            metrics = [
              [
                "AWS/ApplicationELB",
                "TargetResponseTime",
                "LoadBalancer",
                aws_lb.api.arn_suffix
              ]
            ]
            stat   = "Average"
            period = 300
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 6
          width  = 12
          height = 6

          properties = {
            title  = "ECS CPU Utilization"
            region = var.aws_region
            metrics = [
              [
                "AWS/ECS",
                "CPUUtilization",
                "ClusterName",
                aws_ecs_cluster.main.name,
                "ServiceName",
                aws_ecs_service.api.name
              ]
            ]
            stat   = "Average"
            period = 300
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 6
          width  = 12
          height = 6

          properties = {
            title  = "ECS Memory Utilization"
            region = var.aws_region
            metrics = [
              [
                "AWS/ECS",
                "MemoryUtilization",
                "ClusterName",
                aws_ecs_cluster.main.name,
                "ServiceName",
                aws_ecs_service.api.name
              ]
            ]
            stat   = "Average"
            period = 300
          }
        }
      ]
    }
  )
}
