import os.path
import json

from flask import request, Response, url_for, send_from_directory
from werkzeug.utils import secure_filename
from jsonschema import validate, ValidationError

import models
import decorators
import analysis
from chords import app
from database import session
from utils import upload_path

file_schema = {
        "properties": {
            "id": {"type": "integer"}
        },
        "required": ["id"]
    }

@app.route("/uploads/<filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(upload_path(), filename)

@app.route("/api/files", methods=["POST"])
@decorators.require("multipart/form-data")
@decorators.accept("application/json")
def file_post():
    file = request.files.get("file")
    if not file:
        data = {"message": "Could not find file data"}
        return Response(json.dumps(data), 422, mimetype="application/json")

    filename = secure_filename(file.filename)
    db_file = models.File(name=filename)
    session.add(db_file)
    session.commit()
    file.save(upload_path(filename))

    data = db_file.as_dictionary()
    return Response(json.dumps(data), 201, mimetype="application/json")

@app.route("/api/songs", methods=["GET"])
@decorators.accept("application/json")
def songs_get():
    songs = session.query(models.Song)
    data = json.dumps([song.as_dictionary() for song in songs])
    return Response(data, 200, mimetype="application/json")

@app.route("/api/songs/<int:id>/analysis", methods=["GET"])
@decorators.accept("application/json")
def do_analyze(id):
   song = session.query(models.Song).get(id)
   if not song:
       message = "Could not find song with id {}".format(id)
       data = json.dumps({"message": message})
       return Response(data, 404, mimetype="application/json")
   filename = song.file.name
   data = analysis.analyse(upload_path(filename))
   return Response(json.dumps(data), 200, mimetype="application/json")

@app.route("/api/song/<int:id>", methods=["GET"])
@decorators.accept("application/json")
def song_get(id):
    # Assume this always works (bad)
    song = session.query(models.Song).get(id)
    data = json.dumps(song.as_dictionary())
    return Response(data, 200, mimetype="application/json")

@app.route("/api/songs", methods=["POST"])
@decorators.accept("application/json")
@decorators.require("application/json")
def songs_post():
    data = request.json

    # Check that the JSON supplied is valid
    # If not we return a 422 Unprocessable Entity
    try:
        validate(data['file'], file_schema)
    except ValidationError as error:
        data = {"message": error.message}
        return Response(json.dumps(data), 422, mimetype="application/json")

    id = data['file']['id']
    file = session.query(models.File).get(id)
    if not file:
        message = "Could not find file with id {}".format(id)
        data = json.dumps({"message": message})
        return Response(data, 404, mimetype="application/json")

    song = models.Song(file=file)
    session.add(song)
    session.commit()

    data = json.dumps(song.as_dictionary())
    headers = {"Location": url_for("song_get", id=song.id)}
    return Response(data, 201, headers=headers,
                    mimetype="application/json")
