import unittest
import os
import shutil
import json
from urlparse import urlparse
from StringIO import StringIO

# Configure our app to use the testing databse
os.environ["CONFIG_PATH"] = "chords.config.TestingConfig"

from chords import app
from chords import models
from chords.models import Song, File
from chords.utils import upload_path
from chords.database import Base, engine, session

class TestAPI(unittest.TestCase):
    """ Tests for the chords API """

    def setUp(self):
        """ Test setup """
        self.client = app.test_client()

        # Set up the tables in the database
        Base.metadata.create_all(engine)

        # Create folder for test uploads
        os.mkdir(upload_path())

    def tearDown(self):
        """ Test teardown """
        # Remove the tables and their data from the database
        Base.metadata.drop_all(engine)

        # Delete test upload folder
        shutil.rmtree(upload_path())

    def testGetSongs(self):
        s1 = Song(file=File(name="file1.mp3"))
        s2 = Song(file=File(name="file2.mp3"))
        s3 = Song(file=File(name="file3.mp3"))
        session.add_all([s1, s2, s3])
        session.commit()

        response = self.client.get("/api/songs",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data)
        self.assertEqual(len(data), 3)

        song1 = data[0]
        self.assertEqual(song1['file']['name'], 'file1.mp3')
        song2 = data[1]
        self.assertEqual(song2['file']['name'], 'file2.mp3')
        song3 = data[2]
        self.assertEqual(song3['file']['name'], 'file3.mp3')

    def testPostSongs(self):
        f1 = File(name="file1.mp3")
        session.add_all([f1])
        session.commit()

        data = {
            "file": {
                "id": 1
            }
        }

        self.client.post("/api/songs",
            data=json.dumps(data),
            content_type="application/json",
            headers=[("Accept", "application/json")]
        )

        songs = session.query(models.Song).all()
        self.assertEqual(len(songs), 1)
        self.assertEqual(songs[0].id, 1)
        self.assertEqual(songs[0].file.id, 1)
        self.assertEqual(songs[0].file.name, 'file1.mp3')

    def test_get_uploaded_file(self):
        path =  upload_path("test.txt")
        with open(path, "w") as f:
            f.write("File contents")

        response = self.client.get("/uploads/test.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertEqual(response.data, "File contents")

    def test_file_upload(self):
        data = {
            "file": (StringIO("File contents"), "test.txt")
        }

        response = self.client.post("/api/files",
            data=data,
            content_type="multipart/form-data",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data)
        self.assertEqual(urlparse(data["path"]).path, "/uploads/test.txt")

        path = upload_path("test.txt")
        self.assertTrue(os.path.isfile(path))
        with open(path) as f:
            contents = f.read()
        self.assertEqual(contents, "File contents")

