#!/bin/bash

template_file=$(dirname "$0")/template.yaml

if [ "$STAGE_NAME" = "local" ]; then
    command_to_run="samlocal"
else
    command_to_run="sam"
fi

$command_to_run deploy \
    --template-file $template_file \
    --stack-name=$STACK_NAME_dbAppend \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --config-env default \
    --s3-bucket $SAM_S3_BUCKET \
    --s3-prefix $STACK_NAME_dbAppend \
    --region us-east-1 \
    --parameter-overrides \
        "ParameterKey=NetworkStackName,ParameterValue=$VPC_STACK_NAME"

