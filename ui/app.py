import gradio as gr
import requests
import time
import json

from localknow.config import settings

API_URL = f"http://{settings.api_host}:{settings.api_port}"

def run_ingestion(input_dir):
    """Triggers the ingestion pipeline and polls for results."""
    try:
        start_response = requests.post(f"{API_URL}/ingest", json={"input_dir": input_dir}, timeout=10)
        start_data = start_response.json()

        if start_response.status_code == 200 and start_data.get("job_id"):
            job_id = start_data["job_id"]
            yield "Pipeline started... polling for results."

            for _ in range(300):  # Poll for up to 5 minutes
                time.sleep(5)
                result_response = requests.get(f"{API_URL}/results/{job_id}", timeout=10)
                result_data = result_response.json()

                if result_data.get("status") != "running":
                    # Format the final report for display
                    report_str = json.dumps(result_data, indent=2)
                    yield report_str
                    return
                else:
                    yield "Still running..."
            yield "Pipeline timed out."
        else:
            yield f"Error starting pipeline: {start_data.get('detail', 'Unknown error')}"

    except requests.RequestException as e:
        yield f"API request failed: {e}"


def main():
    with gr.Blocks(title="LocalKnow", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# LocalKnow: Knowledge Decomposition Engine")
        with gr.Row():
            with gr.Column(scale=1):
                input_dir = gr.Textbox(label="Input Directory", value="./data")
                run_btn = gr.Button("Run Pipeline", variant="primary")
            with gr.Column(scale=2):
                output_status = gr.Code(label="Pipeline Report", language="json", interactive=False)

        run_btn.click(
            fn=run_ingestion,
            inputs=[input_dir],
            outputs=[output_status]
        )
    demo.launch(server_port=settings.ui_port)


if __name__ == "__main__":
    main() 