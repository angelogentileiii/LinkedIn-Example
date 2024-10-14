#!/bin/bash

# Check whether Localstack or AWS
# Update function name for lambda updates
if [ "$STAGE_NAME" = "local" ]; then
    command_to_run="awslocal"
    # Localstack changes the ARN on each deploy, this ensures the proper ARN is used (fixes error of original ARN persisting)
    FUNCTION_NAME=$($command_to_run cloudformation describe-stacks --stack-name $STACK_NAME_dbAppend --query "Stacks[0].Outputs" --output json | jq -r '.[] | select(.OutputKey == "resource") | .OutputValue')
else
    command_to_run="aws"
    FUNCTION_NAME=$($command_to_run cloudformation describe-stack-resources --stack-name $STACK_NAME_dbAppend --query "StackResources[?ResourceType=='AWS::Lambda::Function'].PhysicalResourceId | [0]" | jq -r '.')
fi

# Layers to update
LayerPandas_ARN=$($command_to_run lambda list-layer-versions --layer-name $LayerPandas_NAME --query 'max_by(LayerVersions, &Version).LayerVersionArn'| jq -r '.')
LayerDbConnect_ARN=$($command_to_run lambda list-layer-versions --layer-name $LayerDbConnect_NAME --query 'max_by(LayerVersions, &Version).LayerVersionArn'| jq -r '.')
LayerDbModel_ARN=$($command_to_run lambda list-layer-versions --layer-name $LayerDbModel_NAME --query 'max_by(LayerVersions, &Version).LayerVersionArn'| jq -r '.')
LayerAioBoto3_ARN=$($command_to_run lambda list-layer-versions --layer-name $LayerAioBoto3_NAME --query 'max_by(LayerVersions, &Version).LayerVersionArn'| jq -r '.')


echo "LayerPandas_ARN $LayerPandas_ARN"
echo "LayerDbConnect_ARN $LayerDbConnect_ARN"
echo "LayerDbModel_ARN $LayerDbModel_ARN"
echo "LayerAioBoto3_ARN $LayerAioBoto3_ARN"


# Get function name from the cloudformation stack
# FUNCTION_NAME=$($command_to_run cloudformation describe-stack-resources --stack-name $STACK_NAME_dbAppend --query "StackResources[?ResourceType=='AWS::Lambda::Function'].PhysicalResourceId | [0]" | jq -r '.')
# FUNCTION_NAME=$($command_to_run cloudformation describe-stacks --stack-name $STACK_NAME_dbAppend --query "Stacks[0].Outputs" --output json | jq -r '.[] | select(.OutputKey == "resource") | .OutputValue')
echo "Function Name: $FUNCTION_NAME"

# Works to update the function with new layer ARNs
$command_to_run lambda update-function-configuration \
--function-name "$FUNCTION_NAME" \
--layers "$LayerPandas_ARN" "$LayerDbConnect_ARN" "$LayerDbModel_ARN" "$LayerAioBoto3_ARN" \
--no-cli-pager