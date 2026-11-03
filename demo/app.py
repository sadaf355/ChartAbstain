"""Gradio demo: shows pre-computed outputs of the untuned and tuned model side by side (no live model call)."""
import json
import os

import gradio as gr

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, 'examples.json'), encoding='utf-8') as fh:
    EX = json.load(fh)['examples']
LABELS = [f"{e['type']}: {e['question'][:70]}" for e in EX]


def show(label):
    e = EX[LABELS.index(label)]
    return e['chart'], e['question'], e['untuned'], e['tuned']


with gr.Blocks(title='Dashboard Q&A with abstention') as demo:
    gr.Markdown(
        '# Dashboard Q&A with abstention\n'
        'Chart questions answered from plotted data, with a one-line reason, and "Cannot be determined from this '
        'chart." when the data does not contain the answer.\n\n'
        '**These outputs are pre-computed** from the held-out evaluation set (untuned Qwen3-4B-Base vs the '
        'LoRA-tuned model). The page does not run a live model.')
    pick = gr.Dropdown(LABELS, value=LABELS[0], label='Example')
    chart = gr.Textbox(label='Chart (text description)', lines=8)
    question = gr.Textbox(label='Question')
    with gr.Row():
        untuned = gr.Textbox(label='Untuned model', lines=4)
        tuned = gr.Textbox(label='Tuned model', lines=4)
    pick.change(show, pick, [chart, question, untuned, tuned])
    demo.load(show, pick, [chart, question, untuned, tuned])

if __name__ == '__main__':
    demo.launch()
