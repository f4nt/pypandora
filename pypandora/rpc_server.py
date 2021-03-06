import eventlet
eventlet.monkey_patch()
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
import pypandora
import _pandora
import logging
from os.path import join, dirname, abspath


THIS_DIR = dirname(abspath(__file__))
CUE_DIR = join(THIS_DIR, "cues")




sound_cue_mapping = {
    "upvote": "upvote.ogg",
    "downvote": "downvote.ogg",
    "station": "station_vote.ogg"
}


def format_song(song):
    """ helper function for formatting songs over rpc """
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "album": song.album,
        "length": song.length,
        "progress": song.progress,
        "art": song.album_art,
        "purchase_itunes": song.purchase_itunes,
        "purchase_amazon": song.purchase_amazon
    }    

class PandoraServerProxy(object):
    def __init__(self):
        self.account = None
        
    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if name == "account" and not attr: raise Exception, "please login first"
        return attr
    
    def login(self, username, password):
        self.account = pypandora.Account(username, password)
        
    def next_song(self):
        station = self._get_current_station()
        song = self.account.current_station.next(finished_cb=station.finish_cb__play_next)
        return format_song(song)
    
    def like_song(self):
        song = self._get_current_song()
        song.like()

    def get_volume(self):
        return pypandora.get_volume()

    def set_volume(self, volume):
        return pypandora.set_volume(volume)

    def play_sound(self, sound):
        sound_file = sound_cue_mapping.get(sound, None)
        if not sound_file: raise Exception, "sound file %s not found" % sound
        _pandora.play_sound(join(CUE_DIR, sound_file))
        
    def dislike_song(self):
        song = self._get_current_song()
        station = self._get_current_station()
        return format_song(song.dislike(finished_cb=station.finish_cb__play_next))
    
    def _get_station(self, station_id):
        station = self.account.stations.get(station_id, None)
        if not station: raise KeyError, "no station by key %s" % station_id
        return station
    
    def _get_current_station(self):
        station = self.account.current_station
        if not station: raise Exception, "no station selected"
        return station
    
    def _get_current_song(self):
        song = self.account.current_song
        if not song: raise Exception, "no current song playing"
        return song

    def stop_song(self):
        self.account.stop()

    def pause_song(self, pause=None):
        song = self._get_current_song()

        if (song.paused and pause is None) or pause is False:
            song.play()
            return True
        else:
            song.pause()
            return False
        
    def get_playlist(self, station_id):
        station = self._get_station(station_id)
        playlist = []
        for song in station.playlist:
            playlist.append(format_song(song))
        return playlist
        
    def play_station(self, station_id):
        station = self._get_station(station_id)
        song = station.play(block=False, finished_cb=station.finish_cb__play_next)
        if not song: return False
        return format_song(song)

    def get_stations(self):
        if not self.account: return {}
        return dict([(k, s.name) for k,s in self.account.stations.iteritems()])
    
    def current_station(self):
        station = self._get_current_station()
        return (station.id, station.name) 
    
    def current_song(self):
        song = self._get_current_song()
        return format_song(song)


    
        
def serve(ip="localhost", port=8123):
    server = SimpleXMLRPCServer((ip, port), allow_none=True)
    server.register_introspection_functions()

    server.register_instance(PandoraServerProxy())    
    t = eventlet.spawn(server.serve_forever)
    t.wait()
    
    
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()
