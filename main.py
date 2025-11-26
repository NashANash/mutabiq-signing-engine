from flask import Flask, request, jsonify
from signer import sign_xml

app = Flask(__name__)


@app.route("/sign", methods=["POST"])
def sign():
    try:
        xml_input = request.data.decode("utf-8")
        signed_xml = sign_xml(xml_input)
        return jsonify({
            "status": "success",
            "signed_xml": signed_xml
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route("/")
def home():
    return "Mutabiq Signing Engine is running."


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)