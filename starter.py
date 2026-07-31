from app import create_app
import os

app = create_app()

if __name__ == "__main__":
    app.logger.warning("""
    ----------------------------
    |  app.run() => flask run  |
    ----------------------------
    """)
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5001, debug=debug)
