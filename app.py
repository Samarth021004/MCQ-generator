from flask import Flask, render_template, request, make_response
from flask_bootstrap import Bootstrap
import spacy
from collections import Counter
import random
import PyPDF2
from PyPDF2 import PdfReader

app = Flask(__name__)
Bootstrap(app)

# Load English tokenizer, tagger, parser, NER, and word vectors
nlp = spacy.load("en_core_web_sm")


def generate_mcqs(text, num_questions=5):
    if not text:
        return []

    # Process the text with spaCy
    doc = nlp(text)

    # Extract sentences and relevant named entities (nouns, proper nouns, and named entities)
    sentences = [sent.text for sent in doc.sents if len(sent.text.split()) > 4]  # Avoid very short sentences
    entities = [ent.text for ent in doc.ents]  # Named entities

    # Ensure we don't request more questions than available sentences
    num_questions = min(num_questions, len(sentences))

    # Randomly sample sentences to generate questions
    selected_sentences = random.sample(sentences, num_questions)
    mcqs = []

    for sentence in selected_sentences:
        # Process sentence to extract relevant parts
        sent_doc = nlp(sentence)
        possible_answers = [ent.text for ent in sent_doc.ents]  # Named entities within the sentence
        
        if not possible_answers:
            possible_answers = [token.text for token in sent_doc if token.pos_ in ["NOUN", "PROPN"]]  # Fallback to nouns

        if not possible_answers or len(possible_answers) < 1:
            continue

        # Pick a main answer
        correct_answer = random.choice(possible_answers)
        
        # Generate question by removing the correct answer from the sentence
        question_stem = sentence.replace(correct_answer, "______", 1)

        # Create distractors
        distractors = list(set(entities) - {correct_answer})
        if len(distractors) < 3:
            # Fallback to some frequent words from the text
            all_nouns = [token.text for token in doc if token.pos_ in ["NOUN", "PROPN"]]
            distractors = list(set(all_nouns) - {correct_answer})

        random.shuffle(distractors)
        answer_choices = [correct_answer] + distractors[:3]
        random.shuffle(answer_choices)

        correct_choice_index = answer_choices.index(correct_answer) + 1  # To match (A), (B), (C) format
        mcqs.append((question_stem, answer_choices, chr(64 + correct_choice_index)))  # chr(64) + 1 = 'A'

    return mcqs


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = ""

        # Check if files were uploaded
        if 'files[]' in request.files:
            files = request.files.getlist('files[]')
            for file in files:
                if file.filename.endswith('.pdf'):
                    # Process PDF file
                    text += process_pdf(file)
                elif file.filename.endswith('.txt'):
                    # Process text file
                    text += file.read().decode('utf-8')
        else:
            # Process manual input
            text = request.form['text']

        # Get the selected number of questions from the dropdown menu
        num_questions = int(request.form['num_questions'])

        mcqs = generate_mcqs(text, num_questions=num_questions)  # Pass the selected number of questions
        mcqs_with_index = [(i + 1, mcq) for i, mcq in enumerate(mcqs)]
        return render_template('mcqs.html', mcqs=mcqs_with_index)

    return render_template('index.html')


def process_pdf(file):
    # Initialize an empty string to store the extracted text
    text = ""

    # Create a PyPDF2 PdfReader object
    pdf_reader = PdfReader(file)

    # Loop through each page of the PDF
    for page_num in range(len(pdf_reader.pages)):
        # Extract text from the current page
        page_text = pdf_reader.pages[page_num].extract_text()
        # Append the extracted text to the overall text
        text += page_text

    return text


if __name__ == '__main__':
    app.run(debug=True)

