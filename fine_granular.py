import grpc
from concurrent import futures
import openai
import json
from arg_services.ranking.v1beta import granularity_pb2_grpc, granularity_pb2

clustering_functions = [
    {
        "name": "cluster_adus",
        "description": "This function aims to cluster Argumentative Discussion Units (ADUs) by analyzing their stances, frames, and meanings in relation to a given query. It first classifies ADUs based on their polarity (supporting or opposing) and further organizes them by their frames (e.g., economic, environmental) to cater to diverse user perspectives. Lastly, it clusters ADUs by meaning to minimize redundancy, ensuring a diverse yet concise representation of arguments. The result is a structured JSON output that systematically presents clustered ADUs for enhanced navigability and comprehension.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The main query or claim that serves as a reference point for clustering ADUs. It represents the central topic around which the arguments are structured."
                },
                "adus": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The textual content of the Argumentative Discussion Unit (ADU), representing a singular argument or premise."
                            },
                            "stance": {
                                "type": "number",
                                "description": "A score representing the ADU's stance in relation to the query, where a positive score indicates support, and a negative score indicates opposition."
                            },
                            "frame": {
                                "type": "number",
                                "description": "A classification score that identifies the perspective or frame from which the ADU approaches the query, such as economic, ethical, or environmental."
                            },
                            "meaning": {
                                "type": "number",
                                "description": "A score assessing the semantic content of the ADU, used to cluster ADUs with similar meanings to reduce redundancy in the argument presentation."
                            },
                            "hierarchic": {
                                "type": "number",
                                "description": "A hierarchical position score indicating the ADU's level of specificity or generality in the context of the argument cluster."
                            }
                        }
                    },
                    "description": "A comprehensive list of ADUs to be evaluated and clustered based on their stance, frame, meaning, and hierarchical position in relation to the query."
                }
            }
        }
    }
]



class GranularityService(granularity_pb2_grpc.GranularityServiceServicer):
    def FineGranularClustering(self, request, context):
        openai.api_key = "key"

        clustering_input = {
            'query': request.query,
            'adus': list(request.adus)
        }

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": json.dumps(clustering_input)}
                ],
                functions=clustering_functions,
            )

            print(response.choices[0])
            clustering_result = json.loads(response.choices[0].message.content)
            predictions = []

            for result in clustering_result:
                # Ensure the result fields are correctly parsed as doubles
                prediction = granularity_pb2.GranularityPrediction(
                    stance=float(result['stance']),
                    frame=float(result['frame']),
                    meaning=float(result['meaning']),
                    hierarchic=float(result['hierarchic'])
                )
                predictions.append(prediction)

            return granularity_pb2.FineGranularClusteringResponse(predictions=predictions)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'An error occurred: {str(e)}')
            return granularity_pb2.FineGranularClusteringResponse()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    granularity_pb2_grpc.add_GranularityServiceServicer_to_server(GranularityService(), server)
    server.add_insecure_port('[::]:50100')
    server.start()
    print("Server started, listening on port 50100")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
