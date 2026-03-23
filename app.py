from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
import os

mongo_uri = os.environ.get("MONGO_URI")
mongodb_host = os.environ.get("MONGO_HOST", "localhost")
mongodb_port = int(os.environ.get("MONGO_PORT", "27017"))

mongo_options = {"serverSelectionTimeoutMS": 2000}
client = MongoClient(mongo_uri, **mongo_options) if mongo_uri else MongoClient(mongodb_host, mongodb_port, **mongo_options)
db = client[os.environ.get("MONGO_DB", "camp2016")]
todos = db[os.environ.get("MONGO_COLLECTION", "todo")]

app = Flask(__name__)
title = "TODO with Flask"
app_version = os.environ.get("APP_VERSION", "v1")
heading = f"ToDo Reminder ({app_version})"


def redirect_url():
	return request.args.get("next") or request.referrer or url_for("tasks")

@app.route("/healthz")
def healthz():
	if os.environ.get("FAIL_LIVENESS", "false").lower() == "true":
		return {"status": "failed", "probe": "liveness"}, 500
	return {"status": "ok", "probe": "liveness", "version": app_version}, 200

@app.route("/readyz")
def readyz():
	if os.environ.get("FAIL_READINESS", "false").lower() == "true":
		return {"status": "failed", "probe": "readiness"}, 500

	try:
		client.admin.command("ping")
	except Exception:
		return {"status": "failed", "probe": "readiness"}, 500

	return {"status": "ok", "probe": "readiness", "version": app_version}, 200

@app.route("/list")
def lists():
	todos_l = list(todos.find())
	return render_template("index.html", a1="active", todos=todos_l, t=title, h=heading)

@app.route("/")
@app.route("/uncompleted")
def tasks():
	todos_l = list(todos.find({"done": "no"}))
	return render_template("index.html", a2="active", todos=todos_l, t=title, h=heading)


@app.route("/completed")
def completed():
	todos_l = list(todos.find({"done": "yes"}))
	return render_template("index.html", a3="active", todos=todos_l, t=title, h=heading)

@app.route("/done")
def done():
	task_id = request.values.get("_id")
	try:
		task = todos.find_one({"_id": ObjectId(task_id)})
	except (InvalidId, TypeError):
		return redirect(redirect_url())

	if task is None:
		return redirect(redirect_url())

	new_status = "no" if task.get("done") == "yes" else "yes"
	todos.update_one({"_id": task["_id"]}, {"$set": {"done": new_status}})
	return redirect(redirect_url())

@app.route("/action", methods=['POST'])
def action():
	name = request.values.get("name", "").strip()
	desc = request.values.get("desc", "").strip()
	date = request.values.get("date", "").strip()
	pr = request.values.get("pr", "").strip()

	if not name or not desc:
		return redirect("/list")

	todos.insert_one({"name": name, "desc": desc, "date": date, "pr": pr, "done": "no"})
	return redirect("/list")

@app.route("/remove")
def remove():
	key = request.values.get("_id")
	try:
		todos.delete_one({"_id": ObjectId(key)})
	except (InvalidId, TypeError):
		pass
	return redirect("/list")

@app.route("/update")
def update():
	task_id = request.values.get("_id")
	try:
		task = todos.find_one({"_id": ObjectId(task_id)})
	except (InvalidId, TypeError):
		task = None
	return render_template("update.html", task=task, h=heading, t=title)

@app.route("/action3", methods=['POST'])
def action3():
	name = request.values.get("name", "").strip()
	desc = request.values.get("desc", "").strip()
	date = request.values.get("date", "").strip()
	pr = request.values.get("pr", "").strip()
	task_id = request.values.get("_id")

	try:
		todos.update_one(
			{"_id": ObjectId(task_id)},
			{"$set": {"name": name, "desc": desc, "date": date, "pr": pr}},
		)
	except (InvalidId, TypeError):
		pass
	return redirect("/")

@app.route("/search", methods=['GET'])
def search():
	key = request.values.get("key", "").strip()
	refer = request.values.get("refer", "").strip()
	todos_l = []
	error = None

	if refer == "id":
		try:
			todos_l = list(todos.find({"_id": ObjectId(key)}))
			if not todos_l:
				error = "No such ObjectId is present"
		except InvalidId:
			error = "Invalid ObjectId format given"
	else:
		if refer in {"name", "desc", "date", "pr"} and key:
			todos_l = list(todos.find({refer: key}))
		else:
			error = "Choose a valid search reference and value"

	if error:
		return render_template("index.html", a2="active", todos=list(todos.find({"done": "no"})), t=title, h=heading, error=error)

	return render_template("searchlist.html", todos=todos_l, t=title, h=heading)

@app.route("/about")
def about():
	return render_template("credits.html", t=title, h=heading)

if __name__ == "__main__":
	env = os.environ.get("FLASK_ENV", "development")
	port = int(os.environ.get("PORT", 5000))
	debug = env != "production"
	app.run(host="0.0.0.0", port=port, debug=debug)
