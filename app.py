import json
from flask import Flask, render_template, jsonify
from parser import parse_raw_data, parse_semantic_data  # Importing your parser logic

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-seo', methods=['GET', 'POST'])
def process_seo():
    # 1. Load video_data.json
    try:
        with open('video_data.json', 'r', encoding='utf-8') as f:
            raw_video_data = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": "video_data.json file not found"}), 404

    # 2. Run parser logic from parser.py
    parsed_results, cat1_count, cat2_count = parse_raw_data(raw_video_data)

    # 3. Return response to front-end
    return jsonify({
        "video_data": raw_video_data,
        "parser_results": parsed_results,
        "histogram": {
            "category_1": cat1_count,
            "category_2": cat2_count
        }
    })

@app.route('/process-seo-optimized', methods=['GET', 'POST'])
def process_seo_optimized():
    # 1. Load video_data.json
    try:
        with open('video_data.json', 'r', encoding='utf-8') as f:
            raw_video_data = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": "video_data.json file not found"}), 404

    # 2. Run semantic optimizer logic from parser.py
    parsed_results, cat1_count, cat2_count = parse_semantic_data(raw_video_data)

    # 3. Return response to front-end
    return jsonify({
        "video_data": raw_video_data,
        "parser_results": parsed_results,
        "histogram": {
            "category_1": cat1_count,
            "category_2": cat2_count
        }
    })

if __name__ == '__main__':
    app.run(debug=True)