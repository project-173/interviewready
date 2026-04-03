from langfuse import get_client
from langfuse.openai import OpenAI
 
# Initialize client
langfuse = get_client()
 
# Define your task function
def my_task(*, item, **kwargs):
    question = item.input # `run_experiment` passes a `DatasetItem` to the task function. The input of the dataset item is available as `item.input`.
    response = OpenAI().chat.completions.create(
        model="gpt-4.1", messages=[{"role": "user", "content": question}]
    )
 
    return response.choices[0].message.content

from langfuse import langfuse_context

def run_experiment(experiment_name, system_prompt):
    # Get dataset from Langfuse
    dataset = langfuse.get_dataset("my-evaluation-dataset")

    for item in dataset.items:
        with item.observe(run_name=experiment_name) as trace_id:

            output = run_my_custom_llm_app(item.input, system_prompt)

            # add custom evaluation results to the experiment trace
            langfuse.score(
                trace_id=trace_id,
                name="exact match",
                value=simple_evaluation(output, item.expected_output)
            )

# Asssert that all events were sent to the LangFuse API
langfuse_context.flush()
langfuse.flush()

def create_dataset_item(dataset_name, trace_id, observation_id):
    langfuse.create_dataset_item(
        dataset_name=dataset_name,
        input={ "text": "hello world" },
        expected_output={ "text": "hello world" },
        # link to a trace
        source_trace_id=trace_id,
        # optional: link to a specific span, event, or generation
        source_observation_id=observation_id
    )