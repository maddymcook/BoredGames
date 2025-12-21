from flask import Flask, jsonify, request

def create_app():
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def home():
        return jsonify({"message": "Hello, Flask!"})

    @app.route("/add", methods=["POST"])
    def add():
        data = request.get_json()
        a = data.get("a")
        b = data.get("b")

        if a is None or b is None:
            return jsonify({"error": "Missing values"}), 400

        return jsonify({"result": a + b})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
