def init_blueprints(app):

    from data5580_hw.routes.user import user
    app.register_blueprint(user)

    from data5580_hw.routes.metrics import metrics
    app.register_blueprint(metrics)

    from data5580_hw.routes.prediction import prediction
    app.register_blueprint(prediction)

    from data5580_hw.routes.model_compare import model_compare
    app.register_blueprint(model_compare)

    from data5580_hw.routes.tasks import tasks
    app.register_blueprint(tasks)
