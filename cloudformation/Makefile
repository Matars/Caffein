REGION?=eu-central-1
STACK_NAME?=caffine-data-pipeline

deploy:
	@echo "Deploying DynamoDB(s) on the environment: $(ENV)"
	@echo "Stack name: $(STACK_NAME)"
	aws cloudformation deploy --stack-name $(STACK_NAME) --template-file data-pipeline.yml --region $(REGION) --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM