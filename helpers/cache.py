# Really generalised LRU cache class that I use frequently. Feel free to modify
# as it may not be too good. THis is like 2 year old code dont judge.
import time
from typing import Dict, Optional, Tuple, Union


# The basic cache class.
class Cache:
    """Cache of objects with IDs."""

    def __init__(self, cache_length : int = 5, cache_limit : int = 500):
        """Establishes a cache and configures the limits.
        Args:
            cache_length (int): How long (in minutes) each cache lasts before
                being removed
            cache_limit (int): A limit to how many objects can be max cached
                before other objects start being removed.
        """
        self._cache = {} # The main cache object.
        self.length = cache_length * 60 # Multipled by 60 to get the length in seconds rather than minutes.
        self._cache_limit = cache_limit
    
    @property
    def cached_items(self) -> int:
        """Returns an int of the lumber of cached items stored."""

        return len(self._cache)
    
    def __len__(self): return self.cached_items()
    
    def cache(self, cache_id : Union[int, str, tuple], cache_obj : object) -> None:
        """Adds an object to the cache."""
        self._cache[cache_id] = {
            "id" : cache_id,
            "expire" : int(time.time()) + self.length,
            "object" : cache_obj
        }
        self.run_checks()
    
    def remove_cache(self, cache_id : Union[int, str, tuple]) -> None:
        """Removes an object from cache."""
        try:
            del self._cache[cache_id]
        except KeyError:
            # It doesnt matter if it fails. All that matters is that no such object exist and if it doesnt exist in the first place, that's already objective complete.
            pass
    
    def get(self, cache_id : Union[int, str, tuple]) -> object:
        """Retrieves a cached object from cache."""

        # Try to get it from cache.
        curr_obj = self._cache.get(cache_id)
        if curr_obj is None:
            return None
        return curr_obj["object"]

    def remove_all_elements(self, pattern: str) -> None:
        # remove all tuple entries with this as a starter

        for key in self._get_cached_ids():
            if isinstance(key, tuple) and key[0] == pattern:
                self.remove_cache(key)
    
    def _get_cached_ids(self) -> list:
        """Returns a list of all cache IDs currently cached."""
        return tuple(self._cache)
    
    def _get_expired_cache(self) -> list:
        """Returns a list of expired cache IDs."""
        current_timestamp = int(time.time())
        expired = []
        for cache_id in self._get_cached_ids():
            # We dont want to use get as that  will soon have the ability to make its own objects, slowing this down.
            if self._cache[cache_id]["expire"] < current_timestamp:
                # This cache is expired.
                expired.append(cache_id)
        return expired
    
    def _remove_expired_cache(self) -> None:
        """Removes all of the expired cache."""
        for cache_id in self._get_expired_cache():
            self.remove_cache(cache_id)
    
    def _remove_limit_cache(self) -> None:
        """Removes all objects past limit if cache reached its limit."""
        
        # Calculate how much objects we have to throw away.
        throw_away_count = len(self._get_cached_ids()) - self._cache_limit

        if not throw_away_count:
            # No levels to throw away
            return
        
        # Get x oldest ids to remove.
        throw_away_ids = self._get_cached_ids()[:throw_away_count]
        for cache_id in throw_away_ids:
            self.remove_cache(cache_id)
    
    def run_checks(self) -> None:
        """Runs checks on the cache."""
        self._remove_expired_cache()
        self._remove_limit_cache()
    
    def get_all_items(self):
        """Generator that lists all of the objects currently cached."""

        # return [obj["object"] for _, obj in self._cache.items()]

        # Make it a generator for performance.
        for obj in self._cache.values(): yield obj["object"]
    
    def get_all_keys(self):
        """Generator that returns all keys of the keys to the cache."""

        return self._get_cached_ids()

# Commonly used cache structures.
# ---- Personal Best Cache ----
class PersonalBestCache:
    """Caches personal best scores for users."""

    def __init__(self) -> None:
        # A dict indexed by mode, beatmap_md5, user_id
        self._cache: Tuple[int, Dict[str, Dict[int, tuple]]] = ({},) * 7
    
    def get_user_pb(self, mode: int, user_id: int, bmap_md5: str, rx: bool) -> Optional[tuple]:
        """Fetches a personal best score for a user. Returns `None` if not found."""

        if rx: mode += 4
        bmap_cache = self._cache[mode].get(bmap_md5)
        if not bmap_cache: return

        return bmap_cache.get(user_id)
    
    def set_user_pb(self, mode: int, user_id: int, bmap_md5: str, score_str: str, rx: bool):
        """Caches a user's personal best score."""

        if rx: mode += 4

        if not self._cache[mode].get(bmap_md5):
            self._cache[mode][bmap_md5] = {}
        
        self._cache[mode][bmap_md5][user_id] = score_str
    
    def del_user_pb(self, mode: int, user_id: int, bmap_md5: str, rx: bool):
        """Deletes a user's personal best from a beatmap. Does NOT raise an
        exception if one was not present in the first place."""

        if rx: mode += 4
        bmap_cache = self._cache[mode].get(bmap_md5)
        if not bmap_cache: return

        try: del bmap_cache[user_id]
        except KeyError: pass
    
    def nuke_bmap_pbs(self, mode: int, bmap_md5: str, rx: bool):
        """Deletes the entire pb cache for a beatmap."""

        if rx: mode += 4
        try: del self._cache[mode][bmap_md5]
        except KeyError: pass

DEF_CACHE_LEN = 120 # 2hrs
DEF_CACHE_COUNT = 1_000

_mode_to_text = (
    "std", "taiko", "catch", "mania"
)

# Maybe should've used smth similar to above.
class LeaderboardCache:
    """A class for managing the entirety of the leaderboard caching.
    Stores `LbCacheResult`."""

    def __init__(self) -> None:
        self.vn_std = Cache(
            cache_length= DEF_CACHE_LEN,
            cache_limit= DEF_CACHE_COUNT,
        )
        self.vn_taiko = Cache(
            cache_length= DEF_CACHE_LEN,
            cache_limit= DEF_CACHE_COUNT,
        )
        self.vn_catch = Cache(
            cache_length= DEF_CACHE_LEN,
            cache_limit= DEF_CACHE_COUNT,
        )
        self.vn_mania = Cache(
            cache_length= DEF_CACHE_LEN,
            cache_limit= DEF_CACHE_COUNT,
        )

        # Relax
        self.rx_std = Cache(
            cache_length= DEF_CACHE_LEN,
            cache_limit= DEF_CACHE_COUNT,
        )
        self.rx_taiko = Cache(
            cache_length= DEF_CACHE_LEN,
            cache_limit= DEF_CACHE_COUNT,
        )
        self.rx_catch = Cache(
            cache_length= DEF_CACHE_LEN,
            cache_limit= DEF_CACHE_COUNT,
        )
        # RX has no mania
    
    def get_lb_cache(self, mode: int, rx: bool) -> Cache:
        """Returns a `Cache` object corresponding to the `mode` + `rx` combo."""
        
        prefix = "rx" if rx else "vn"
        suffix = _mode_to_text[mode]

        return self.__getattribute__(f"{prefix}_{suffix}")

    def clear_lb_cache(self, lb_cache: Cache, bmap_md5: str) -> None:
        """Clears given leaderboard cache object"""

        lb_cache.remove_all_elements(bmap_md5) # cool idea james!

class LbCacheResult:
    """Simple lb cache result, storing cached information."""

    __slots__ = ("count", "scores")

    def __init__(self, count: int, scores: tuple) -> None:
        self.count = count
        self.scores = scores
