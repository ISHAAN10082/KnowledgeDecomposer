import gradio as gr
import requests
import json

from intellidoc.config import settings

API_URL = f"http://{settings.api_host}:{settings.api_port}"

def process_document(file):
    """Sends the uploaded file to the backend for processing and returns the results."""
    if file is None:
        return None, "Please upload a document.", None

    try:
        files = {'file': (file.name, open(file.name, 'rb'))}
        response = requests.post(f"{API_URL}/extract", files=files, timeout=300)
        
        if response.status_code == 200:
            result_data = response.json()
            
            image_output = file.name
            
            extracted_json = result_data.get("extracted_data")
            if not extracted_json:
                 return image_output, "Could not extract any data.", "Extraction failed or returned no data."

            json_output = json.dumps(extracted_json.get("extracted_data", {}), indent=2)
            
            justification_data = extracted_json.get("field_justifications", {})
            confidence = extracted_json.get('confidence_score', 0)
            
            justification = f"**Overall Confidence Score:** {confidence:.2f}\n\n---"
            justification += "\n\n"
            justification += "\n".join([f"- **{k.replace('_', ' ').title()}**: {v}" for k, v in justification_data.items()])

            return image_output, json_output, justification
        else:
            return None, f"Error: {response.text}", None

    except requests.RequestException as e:
        return None, f"API request failed: {e}", None
    except Exception as e:
        return None, f"An error occurred: {e}", None

def main():
    with gr.Blocks(title="IntelliDoc Extractor", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # IntelliDoc Extractor: From Unstructured to Actionable Data
            Upload an invoice (PDF or image) to see how our vision-enabled, self-correcting AI pipeline extracts structured data in real-time.
            """
        )
        
        with gr.Row():
            upload_button = gr.File(label="Upload Invoice", file_types=["pdf", "image"])
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## Original Document")
                image_display = gr.Image(type="filepath", label="Document View")
            with gr.Column(scale=1):
                gr.Markdown("## Extracted Data")
                json_display = gr.Code(label="JSON Output", language="json", interactive=False)
        
        with gr.Row():
            gr.Markdown("## Justification & Confidence")
        with gr.Row():
            justification_display = gr.Markdown()

        upload_button.change(
            fn=process_document,
            inputs=[upload_button],
            outputs=[image_display, json_display, justification_display]
        )

    demo.launch(server_port=settings.ui_port, share=True)


if __name__ == "__main__":
    main() 