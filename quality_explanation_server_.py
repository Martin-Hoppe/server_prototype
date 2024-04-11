import grpc
from concurrent import futures
import openai
import json
from arg_services.quality.v1beta import quality_pb2, quality_pb2_grpc

# Define your custom functions according to specific analysis needs
evaluation_functions = [
    {
        'name': 'evaluate_argument',
        'description': 'Evaluates which premise is more convincing based on the provided arguments',
        'parameters': {
            'type': 'object',
            'properties': {
                'claim': {'type': 'string', 'description': 'The main claim.'},
                'premise1': {'type': 'string', 'description': 'First premise to evaluate.'},
                'premise2': {'type': 'string', 'description': 'Second premise to evaluate.'}
            }
        }
    }
]

class QualityExplanationService(quality_pb2_grpc.QualityExplanationServiceServicer):
    def Explain(self, request, context):
        openai.api_key = "your-openai-api-key"

        prompt = {
            'claim': request.claim,
            'premise1': request.premise1,
            'premise2': request.premise2
        }

        try:
            # Enhanced OpenAI API call with function calling
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": json.dumps(prompt)}
                ],
                functions=evaluation_functions,
                function_call={
                    'name': 'evaluate_argument',
                    'arguments': prompt
                },
                function_call_mode='auto'  # Automatically perform function calling
            )

            # Handling the extracted JSON response
            evaluations = json.loads(response.choices[0].message['content'])
            dimension_name = "Standard Evaluation"
            global_convincingness = quality_pb2.PREMISE_CONVINCINGNESS_UNSPECIFIED

            # Example logic to pick the global convincingness
            if evaluations['more_convincing_premise'] == 'premise1':
                global_convincingness = quality_pb2.PREMISE_CONVINCINGNESS_PREMISE_1
            elif evaluations['more_convincing_premise'] == 'premise2':
                global_convincingness = quality_pb2.PREMISE_CONVINCINGNESS_PREMISE_2

            # Create the QualityDimension
            quality_dimension = quality_pb2.QualityDimension(
                convincingness=global_convincingness,
                premise1=float(evaluations['premise1_score']),
                premise2=float(evaluations['premise2_score']),
                explanation=evaluations['explanation'],
                methods=["GPT-4 Evaluation"]
            )

            return quality_pb2.ExplainResponse(
                global_convincingness=global_convincingness,
                dimensions={dimension_name: quality_dimension}
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'An error occurred: {str(e)}')
            return quality_pb2.ExplainResponse()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    quality_pb2_grpc.add_QualityExplanationServiceServicer_to_server(QualityExplanationService(), server)
    server.add_insecure_port('[::]:50100')
    server.start()
    print("Server started, listening on port 50100")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()