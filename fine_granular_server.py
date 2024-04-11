import grpc
from concurrent import futures
import openai
import json
from arg_services.ranking.v1beta import ranking_pb2, ranking_pb2_grpc

clustering_functions = [
    {
        'name': 'cluster_adus',
        'description': 'Predicts clustering scores for a list of ADUs based on a given query',
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': 'The main query against which ADUs are ranked.'},
                'adus': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of argumentative discussion units to be evaluated.'
                }
            }
        }
    }
]

class GranularityService(ranking_pb2_grpc.GranularityServiceServicer):
    def FineGranularClustering(self, request, context):
        openai.api_key = "your-openai-api-key"

        # Construct function input arguments based on the request
        clustering_input = {
            'query': request.query,
            'adus': list(request.adus)
        }

        try:
            # OpenAI GPT model call with custom function usage
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": json.dumps(clustering_input)}
                ],
                functions=clustering_functions,
                function_call={
                    'name': 'cluster_adus',
                    'arguments': clustering_input
                },
                function_call_mode='auto'
            )

            clustering_result = json.loads(response.choices[0].message['content'])
            predictions = []

            for result in clustering_result:
                prediction = ranking_pb2.GranularityPrediction(
                    stance=result['stance'],
                    frame=result['frame'],
                    meaning=result['meaning'],
                    hierarchic=result['hierarchic']
                )
                predictions.append(prediction)

            return ranking_pb2.FineGranularClusteringResponse(predictions=predictions)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'An error occurred: {str(e)}')
            return ranking_pb2.FineGranularClusteringResponse()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ranking_pb2_grpc.add_GranularityServiceServicer_to_server(GranularityService(), server)
    server.add_insecure_port('[::]:50200')
    server.start()
    print("Server started, listening on port 50200")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()