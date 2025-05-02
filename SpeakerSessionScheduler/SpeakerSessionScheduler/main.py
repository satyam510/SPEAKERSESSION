from app import app
from routes import api, main
from docs import swagger_blueprint

# Register blueprints
app.register_blueprint(main)  # Register main blueprint for web routes
app.register_blueprint(api)   # Register API blueprint
app.register_blueprint(swagger_blueprint)  # Register Swagger docs

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
