from edu_test import *
import boto3
import time
import csv 
etl = EduTest()
etl.init()
make_res = EduResult()

def SNS_topic(access_key_id, secret_access_key, region='us-east-1'):
    sns_client = boto3.client('sns', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)
    topic_name = 'ReminderTopic'
    try:
        # List all topics
        response = sns_client.list_topics()
        topics = response.get('Topics', [])
        numberOfTopics = len(topics)
        if numberOfTopics>1:
            make_res.add_results("More than one SNS topic exist", EduResult.Fail)
            return
        for topic in topics:
            if topic_name in topic.get('TopicArn', ''):
                make_res.add_results("SNS Topic Check", EduResult.Pass)
                return
        make_res.add_results("SNS Topic not found", EduResult.Fail)
    except Exception as e:
        make_res.add_results("SNS Topic Check", EduResult.Fail)

def IAM_Role(access_key_id, secret_access_key, region='us-east-1'):
    role_name='ReminderFunctionRole'
    iam = boto3.client('iam', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)
    try:
        response = iam.get_role(RoleName=role_name)
        role_info = response['Role']
        make_res.add_results("Role-creation check", EduResult.Pass)

    except iam.exceptions.NoSuchEntityException:
        make_res.add_results(f" Role '{role_name}' doesnt exist", EduResult.Fail)

def check_lambda_function(access_key_id, secret_access_key, region='us-east-1'):
    lambda_function_name='ReminderFunction'
    actual_role_name='ReminderFunctionRole'
    runtime = 'python3.9'
    lambda_client = boto3.client('lambda', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)
    print("Inside lambda function")
    try:
        response = lambda_client.get_function(FunctionName=lambda_function_name)
        function_info = response['Configuration']

        #Check Role attached with Lambda
        attached_role_arn = function_info['Role']
        attached_role_name = attached_role_arn.split('/')[-1]
        print("The attached role is:", attached_role_name)

        if attached_role_name == actual_role_name:
            print("Correct Role Attached")
            make_res.add_results("Lambda Role Check", EduResult.Pass)
        else:
            print("The role attached with Lambda is not RoleForMLServices")
            make_res.add_results("Correct role not attached", EduResult.Fail)

        #Check Runtime

        actual_runtime = function_info['Runtime']
        print("Actual runtime", actual_runtime)
        if runtime == actual_runtime:
            print("Correct Runtime Python 3.9 selected")
            make_res.add_results("Lambda Runtime Check", EduResult.Pass)
        else:
            make_res.add_results("Python 3.9 is not selected", EduResult.Fail)

    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"Lambda function '{lambda_function_name}' not found. Function check: FAILED")
        make_res.add_results("Lambda Function Check", EduResult.Fail)

def get_access_policy(access_key_id, secret_access_key, region='us-east-1'):
    sns_client = boto3.client('sns', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)

    topic_name = 'ReminderTopic'
    expected_access_policy_id = 'ReminderID'

    try:
        response = sns_client.list_topics()
        topics = response.get('Topics', [])
        topic_arn = None

        for topic in topics:
            if topic_name in topic.get('TopicArn', ''):
                topic_arn = topic.get('TopicArn')
                break

        # if not topic_arn:
        #     print(f"No SNS topic with name '{topic_name}' found.")
        #     make_res.add_results("SNS Topic Access Policy Check", EduResult.Fail)
        #     return
        # Get the access policy of the SNS topic
        access_policy_response = sns_client.get_topic_attributes(TopicArn=topic_arn)
        access_policy = access_policy_response.get('Attributes', {}).get('Policy')

        if access_policy:
            print(f"Access policy for SNS topic '{topic_name}':")
            print(access_policy)

            access_policy_json = json.loads(access_policy)

            # Check if "Id" in the access policy matches the expected value
            if access_policy_json.get('Id') == expected_access_policy_id:
                make_res.add_results("SNS Topic Access Policy Updated", EduResult.Pass)
            else:
                make_res.add_results("SNS Topic Access Policy not updated", EduResult.Fail)
        else:
            make_res.add_results("No SNS Topic Access Policy Found", EduResult.Fail)

    except Exception as e:
        make_res.add_results("SNS Topic Access Policy Check", EduResult.Fail)

def SQS_Queue(access_key_id, secret_access_key, region='us-east-1'):
    sqs_client = boto3.client('sqs', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)
    queue_name = 'ReminderQueue'

    try:
        # List all queues with the specified name
        response = sqs_client.list_queues()
        queues = response.get('QueueUrls', [])
        numberOfQueues=len(queues)
        if numberOfQueues>1:
            make_res.add_results("More than one queues exist", EduResult.Fail)
            return

        if queue_name in queues[0]:
            print(f"SQS queue '{queue_name}' found.")
            make_res.add_results("SQS Queue Check", EduResult.Pass)
        else:
            print(f"No or more than one SQS queue with name '{queue_name}' found.")
            make_res.add_results("ReminderQueue not found", EduResult.Fail)


    except Exception as e:
        print(f"An error occurred while checking SQS queue: {str(e)}")
        make_res.add_results("SQS Queue Check", EduResult.Fail)

def sqs_access_policy(access_key_id, secret_access_key, region='us-east-1'):
    sqs_client = boto3.client('sqs', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)

    queue_name = 'ReminderQueue'

    try:
        # Get the URL of the SQS queue by name
        response = sqs_client.get_queue_url(QueueName=queue_name)
        queue_url = response.get('QueueUrl')

        # Get the attributes of the SQS queue
        queue_attributes_response = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['All'])
        queue_attributes = queue_attributes_response.get('Attributes', {})

        # Get the access policy of the SQS queue
        access_policy = queue_attributes.get('Policy')

        if access_policy:
            print(f"Access policy for SQS queue '{queue_name}':")
            print(access_policy)

            # Parse the access policy JSON
            access_policy_json = json.loads(access_policy)

            # Check if the "Service" key is present in any statement
            if access_policy_json.get('Statement'):
                for statement in access_policy_json['Statement']:
                    principal = statement.get('Principal', {})
                    if isinstance(principal, dict) and 'Service' in principal:
                        print(f"Access policy contains 'Service' key for SQS queue '{queue_name}'.")
                        make_res.add_results("SQS Access Policy Check", EduResult.Pass)
                        return
            print(f"Access policy does not contain 'Service' key for SQS queue '{queue_name}'.")
            make_res.add_results("Access Policy not updated", EduResult.Fail)
        else:
            print(f"No access policy found for SQS queue '{queue_name}'.")
            make_res.add_results("SQS Access Policy not found", EduResult.Fail)

    except Exception as e:
        print(f"An error occurred while checking SQS access policy: {str(e)}")
        make_res.add_results("SQS Access Policy Check", EduResult.Fail)


def SNS_subscription_SQS(access_key_id, secret_access_key, region='us-east-1'):
    sns_client = boto3.client('sns', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)
    sqs_client = boto3.client('sqs', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)

    queue_name = 'ReminderQueue'

    try:
        # Get the URL of the SQS queue by name
        response = sqs_client.get_queue_url(QueueName=queue_name)
        queue_url = response.get('QueueUrl')
        queue_arn = response.get('QueueArn')

        print("Queuer URL",response)

        # Get the list of subscriptions for the SNS topic
        response = sns_client.list_subscriptions()
        subscriptions = response.get('Subscriptions', [])
        print("Subscriptions: ", subscriptions)

        # Check if there is a subscription for the SQS queue endpoint
        for subscription in subscriptions:
            if subscription.get('Protocol') == 'sqs' and 'ReminderQueue' in subscription.get('Endpoint', ''):
                print(f"SNS subscription found for SQS queue '{queue_name}'.")
                make_res.add_results("SNS Subscription Check", EduResult.Pass)
                return

        print(f"No SNS subscription found for SQS queue '{queue_name}'.")
        make_res.add_results("SNS subscription not created", EduResult.Fail)

    except Exception as e:
        print(f"An error occurred while checking SNS subscription: {str(e)}")
        make_res.add_results("SNS Subscription for SQS not found", EduResult.Fail)

def SNS_subscription_Email(access_key_id, secret_access_key, region='us-east-1'):
    sns_client = boto3.client('sns', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)
    sqs_client = boto3.client('sqs', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)

    try:
        # Get the list of subscriptions for the SNS topic
        response = sns_client.list_subscriptions()
        subscriptions = response.get('Subscriptions', [])
        next_token = response.get('NextToken')
        print("Subscriptions>>>>>>", subscriptions)
        print("Subscriptions response??????", response)
        print("Next token>>>>>", next_token)

        while next_token:
            response = sns_client.list_subscriptions(NextToken=next_token)
            subscriptions_next_token = response.get('Subscriptions', [])
            next_token = response.get('NextToken')
            print("subsbsbss",subscriptions_next_token)

        if subscriptions == []:
            make_res.add_results("SNS subscription not found for email", EduResult.Fail)
        
        else:
        for subscription in subscriptions_next_token:
            print("sub", subscription)
            if subscription.get('Protocol') == 'email':
                print(f"SNS subscription found for Email")
                make_res.add_results("SNS Subscription for email", EduResult.Pass)
                return
            
            print(f"No SNS subscription found for email")
            make_res.add_results("SNS subscription not found for email", EduResult.Fail)

    except Exception as e:
        print(f"An error occurred while checking SNS subscription: {str(e)}")
        make_res.add_results("SNS Subscription for Email not found", EduResult.Fail)

def SQS_messages(access_key_id, secret_access_key, region='us-east-1'):
    sqs_client = boto3.client('sqs', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)

    queue_name = 'ReminderQueue'

    try:
        # Get the URL of the SQS queue by name
        response = sqs_client.get_queue_url(QueueName=queue_name)
        queue_url = response.get('QueueUrl')

        if not queue_url:
            print(f"No SQS queue with name '{queue_name}' found.")
            make_res.add_results("SQS Messages Check", EduResult.Fail)
            return

        # Receive messages from the queue
        response = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)

        # Check if any messages were received
        if 'Messages' in response:
            print(f"SQS queue '{queue_name}' has messages in the 'Messages' section.")
            make_res.add_results("SQS Messages Check", EduResult.Pass)
        else:
            print(f"SQS queue '{queue_name}' does not have any messages in the 'Messages' section.")
            make_res.add_results("SQS doesnt have any messages", EduResult.Fail)

    except Exception as e:
        print(f"An error occurred while checking SQS messages: {str(e)}")
        make_res.add_results("SQS Messages Check", EduResult.Fail)

def Eventbridge_rule(access_key_id, secret_access_key, region='us-east-1'):
    eventbridge_client = boto3.client('events', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region_name=region)

    rule_name = 'ReminderSchedule'  

    try:
        # List all rules in EventBridge
        response = eventbridge_client.list_rules(NamePrefix=rule_name)

        # Check if the rule exists
        rules = response.get('Rules', [])
        for rule in rules:
            if rule['Name'] == rule_name:
                print(f"EventBridge rule '{rule_name}' found.")
                make_res.add_results("EventBridge Rule Check", EduResult.Pass)
                return

        print(f"No EventBridge rule with name '{rule_name}' found.")
        make_res.add_results("No EventBridge Rule found", EduResult.Fail)

    except Exception as e:
        print(f"An error occurred while checking EventBridge rules: {str(e)}")
        make_res.add_results("EventBridge Rule Check", EduResult.Fail)




if __name__ == "__main__":
    csv_file = 'credentials_IAMLabUser.csv'
    print("access:",os.getenv("access_key_id"))
    print("secret access:",os.getenv("secret_access_key"))
    try:
        SNS_topic(os.getenv("access_key_id"), os.getenv("secret_access_key"))
        IAM_Role(os.getenv("access_key_id"), os.getenv("secret_access_key"))
        check_lambda_function(os.getenv("access_key_id"), os.getenv("secret_access_key"))
        get_access_policy(os.getenv("access_key_id"), os.getenv("secret_access_key"))
        SQS_Queue(os.getenv("access_key_id"), os.getenv("secret_access_key"))
        sqs_access_policy(os.getenv("access_key_id"), os.getenv("secret_access_key"))
        SNS_subscription_SQS(os.getenv("access_key_id"), os.getenv("secret_access_key"))
        SNS_subscription_Email(os.getenv("access_key_id"), os.getenv("secret_access_key"))
        SQS_messages(os.getenv("access_key_id"), os.getenv("secret_access_key"))
        Eventbridge_rule(os.getenv("access_key_id"), os.getenv("secret_access_key"))

    except:
        print("Error Running function")



etl.post_results(make_res)
