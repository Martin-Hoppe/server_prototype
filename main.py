import grpc
from concurrent import futures
import openai
import json
from arg_services.quality.v1beta import explanation_pb2_grpc, explanation_pb2
from arg_services.quality.v1beta.explanation_pb2_grpc import QualityExplanationServiceServicer

# Define your custom functions according to specific analysis needs
evaluation_functions = [
    {
        'name': 'evaluate_argument',
        'description': 'Evaluate which premise is more convincing based on the provided arguments and give it a score',
        'parameters': {
            'type': 'object',
            'properties': {
                'claim': {'type': 'string', 'description': 'The main claim.'},
                'premise1': {'type': 'string', 'description': 'First premise to evaluate.'},
                'premise2': {'type': 'string', 'description': 'Second premise to evaluate.'},
                'premise1_score': {'type': 'string', 'description': 'The score for premise 1 as a float'},
                'premise2_score': {'type': 'string', 'description': 'The score for premise 2 as a float'},
                'explanation' : {'type': 'string', 'description': 'Why you scored as you did'}
            }
        }
    }
]

class QualityExplanationService(QualityExplanationServiceServicer):
    def Explain(self, request, context):
        openai.api_key = "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"

        prompt = {
            'claim': request.claim,
            'premise1': request.premise1,
            'premise2': request.premise2
        }

        try:
            # Enhanced OpenAI API call with function calling
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": json.dumps(prompt)}
                ],
                functions=evaluation_functions,
            )

            # Handling the extracted JSON response
            print(response.choices[0].message.content)
            evaluations = json.loads(response.choices[0].message.content)
            dimension_name = "Standard Evaluation"

            # Example logic to pick the global convincingness
            if evaluations['premise1_score'] > evaluations['premise2_score']:
                global_convincingness = explanation_pb2.PREMISE_CONVINCINGNESS_PREMISE_1
            elif evaluations['premise1_score'] == evaluations['premise2_score']:
                global_convincingness = explanation_pb2.PREMISE_CONVINCINGNESS_UNSPECIFIED
            else:
                global_convincingness = explanation_pb2.PREMISE_CONVINCINGNESS_PREMISE_2
            print(global_convincingness)
            # Create the QualityDimension
            quality_dimension = explanation_pb2.QualityDimension(
                convincingness=global_convincingness,
                premise1=evaluations['premise1_score'],
                premise2=evaluations['premise2_score'],
                explanation=evaluations['explanation'],
                methods=["GPT-4 Evaluation"]
            )
            return explanation_pb2.ExplainResponse(
                global_convincingness=global_convincingness,
                dimensions={dimension_name: quality_dimension}
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'An error occurred: {str(e)}')
            return explanation_pb2.ExplainResponse()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    explanation_pb2_grpc.add_QualityExplanationServiceServicer_to_server(QualityExplanationService(), server)
    server.add_insecure_port('[::]:50100')
    server.start()
    print("Server started, listening on port 50100")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()