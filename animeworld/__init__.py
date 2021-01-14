import requests
from bs4 import BeautifulSoup
import youtube_dl
import re
# import json

HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}

def find(animeName):
	# def mySort(Anime):
	# 	return len(Anime.name.replace(animeName, ""))

	ret = {}

	search = "https://www.animeworld.tv/search?keyword={}".format(animeName.replace(" ", "%20"))
	sb_get = requests.get(search, headers = HDR)
	soupeddata = BeautifulSoup(sb_get.content, "html.parser")

	page_result = soupeddata.find("div", { "class" : "film-list" }).find_all("a", { "class" : "name" })
	for x in page_result:
		# ret.append({x.get_text(): x.get("href")})
		ret[x.get_text()] = f"https://www.animeworld.tv{x.get('href')}"

	# ret.sort(key=mySort)
	return ret
	

class Anime:
	mapped = {
		2:"DoodStream",
		3:"VVVVID",
		4:"YouTube",
		8:"Streamtape",
		9:"AnimeWorld Server",
		10:"Beta Server",
		11:"OkStream",
		15:"NinjaStream",
		17:"Userload",
		18:"VUP"
	}

	def __init__(self, link):
		self.link = link
		self.html = requests.get(self.link, headers = HDR, cookies={}).content
		# self.nome = self.getName()
		# self.server = self.getServer()
		# self.trama = self.getTrama()
		# self.info = self.getInfo()

	### INFO ####

	def getServer(self): # Provider dove sono hostati gli episodi
		soupeddata = BeautifulSoup(self.html, "html.parser")
		block = soupeddata.find("span", { "class" : "servers-tabs" })

		if block == None: raise AnimeNotAvailable(self.getName())

		providers = block.find_all("span", { "class" : "server-tab" })
		return [int(x["data-name"]) for x in providers]

	def getTrama(self): # Trama dell'anime 
		soupeddata = BeautifulSoup(self.html, "html.parser")
		return soupeddata.find("div", { "class" : "desc" }).get_text()

	def getInfo(self): # Informazioni dell'anime
		soupeddata = BeautifulSoup(self.html, "html.parser")
		block = soupeddata.find("div", { "class" : "info" }).find("div", { "class" : "row" })

		tName = [x.get_text() for x in block.find_all("dt")]
		tInfo = []
		for x in block.find_all("dd"):
			txt = x.get_text()
			if len(txt.split(',')) > 1:
				tInfo.append([x.strip() for x in txt.split(',')])
			else:	
				tInfo.append(txt.strip())

		return dict(zip(tName, tInfo))

	def getName(self): # Nome dell'anime
		soupeddata = BeautifulSoup(self.html, "html.parser")
		return soupeddata.find("h1", { "id" : "anime-title" }).get_text()

	#############

	def getEpisodes(self): # Ritorna una lista di Episodi
		eps = []
		soupeddata = BeautifulSoup(self.html, "html.parser")
		raw = {}
		setEps = set(())
		for idProvider in self.getServer():
			epBox = soupeddata.find("div", { "class" : "server", "data-name": str(idProvider)})
			ep_links = epBox.find_all("a")
			for x in ep_links:
				if x.get_text() not in raw.keys(): raw[x.get_text()] = {}

				raw[x.get_text()][idProvider] = "https://www.animeworld.tv" + x.get("href")

		for episode in raw:
			links = self.setServer(raw[episode])
			ep = Episodio(episode, links)
			eps.append(ep)

		return eps

	def setServer(self, links):
		ret = []
		for link in links:
			if link == 3: 
				ret.append(VVVVID(links[link], link, self.mapped[link]))
			elif link == 4:
				ret.append(YouTube(links[link], link, self.mapped[link]))
			elif link == 9:
				ret.append(AnimeWorld_Server(links[link], link, self.mapped[link]))
			elif link == 8:
				ret.append(Streamtape(links[link], link, self.mapped[link]))
			else:
				ret.append(Server(links[link], link, self.mapped[link]))
		ret.sort(key=self.sortServer)
		return ret

	def sortServer(self, elem): # Ordina i server per importanza
		if isinstance(elem, VVVVID): return 0
		elif isinstance(elem, YouTube): return 1
		elif isinstance(elem, AnimeWorld_Server): return 2
		elif isinstance(elem, Streamtape): return 3
		else: return 4



class Episodio:
	# links = []
	def __init__(self, number, links):
		self.number = number
		self.links = links

	def download(self, title="Episodio"): # Scarica l'episodio con il primo link nella lista
		return self.links[0].download(title)

### Server ###

class Server:
	def __init__(self, link, Nid, name):
		self.link = link
		self.Nid = Nid
		self.name = name
		self.HDR = HDR

	def sanitize(self, title):
		illegal = ['#','%','&','{','}', '\\','<','>','*','?','/','$','!',"'",'"',':','@','+','`','|','=']
		for x in illegal:
			title = title.replace(x, '')
		return title

	def download(self, *args):
		raise ServerNotSupported(self.name)

class AnimeWorld_Server(Server):
	def getFileLink(self):
		anime_id = self.link.split("/")[-1]
		video_link = "https://www.animeworld.tv/api/episode/ugly/serverPlayerAnimeWorld?id={}".format(anime_id)

		sb_get = requests.get(video_link, headers = self.HDR, cookies={})
		if sb_get.status_code == 200:
			soupeddata = BeautifulSoup(sb_get.content, "html.parser")
			raw_ep = soupeddata.find("video", { "id" : "video-player" }).find("source", { "type" : "video/mp4" })

			self.HDR["Referer"] = video_link
			return raw_ep.get("src")

	def download(self, title="Episodio"):
		title = self.sanitize(title)
		r = requests.get(self.getFileLink(), headers = self.HDR, stream = True)

		if r.status_code == 200:
			# download started 
			with open(f"{title}.mp4", 'wb') as f:
				total_length = int(r.headers.get('content-length'))
				for chunk in r.iter_content(chunk_size = 1024*1024):
					if chunk: 
						f.write(chunk)
						f.flush()
				else:
					return True
		return False

class VVVVID(Server):
	def getFileLink(self):
		anime_id = self.link.split("/")[-1]
		external_link = "https://www.animeworld.tv/api/episode/ugly/serverPlayerAnimeWorld?id={}".format(anime_id)

		sb_get = requests.get(self.link, headers = self.HDR, cookies={})
		if sb_get.status_code == 200:
			sb_get = requests.get(external_link, headers = self.HDR, cookies={})
			soupeddata = BeautifulSoup(sb_get.content, "html.parser")
			if sb_get.status_code == 200:
					
				raw = soupeddata.find("a", { "class" : "VVVVID-link" })
				return raw.get("href")

	def download(self, title="Episodio"):
		title = self.sanitize(title)

		class MyLogger(object):
			def debug(self, msg):
				pass
			def warning(self, msg):
				pass
			def error(self, msg):
				print(msg)
				return False
		def my_hook(d):
			if d['status'] == 'finished':
				return True

		ydl_opts = {
			'outtmpl': title+'.%(ext)s',
			'logger': MyLogger(),
			'progress_hooks': [my_hook],
		}
		with youtube_dl.YoutubeDL(ydl_opts) as ydl:
			ydl.download([self.getFileLink()])

class YouTube(Server):
	def getFileLink(self):
		anime_id = self.link.split("/")[-1]
		external_link = "https://www.animeworld.tv/api/episode/ugly/serverPlayerAnimeWorld?id={}".format(anime_id)

		sb_get = requests.get(self.link, headers = self.HDR, cookies={})
		if sb_get.status_code == 200:
			sb_get = requests.get(external_link, headers = self.HDR, cookies={})
			soupeddata = BeautifulSoup(sb_get.content, "html.parser")
			if sb_get.status_code == 200:
				yutubelink_raw = re.findall("https://www.youtube.com/embed/...........", soupeddata.prettify())[0]
				return yutubelink_raw.replace("embed/", "watch?v=")

	def download(self, title="Episodio"):
		title = self.sanitize(title)

		class MyLogger(object):
			def debug(self, msg):
				pass
			def warning(self, msg):
				pass
			def error(self, msg):
				print(msg)
				return False
		def my_hook(d):
			if d['status'] == 'finished':
				return True

		ydl_opts = {
			'outtmpl': title+'.%(ext)s',
			'logger': MyLogger(),
			'progress_hooks': [my_hook],
		}
		with youtube_dl.YoutubeDL(ydl_opts) as ydl:
			ydl.download([self.getFileLink()])

class Streamtape(Server):
	def getFileLink(self):
		sb_get = requests.get(self.link, headers = self.HDR, cookies={})
		if sb_get.status_code == 200:
			soupeddata = BeautifulSoup(sb_get.content, "html.parser")
			site_link = soupeddata.find("div", { "id" : "external-downloads" }).find("a", { "class" : "btn-streamtape" }).get("href")
			sb_get = requests.get(site_link, headers = self.HDR, cookies={})
			if sb_get.status_code == 200:

				soupeddata = BeautifulSoup(sb_get.content, "html.parser")

				mp4_link = "https://" + re.search(r"document\.getElementById\(\'vid\'\+\'eolink\'\)\.innerHTML = \"\/\/(.+)\'\;", soupeddata.prettify()).group(1)
				return mp4_link.replace(" ", "").replace("+", "").replace("\'", "").replace("\"", "")

	def download(self, title="Episodio"):
		title = self.sanitize(title)
		r = requests.get(self.getFileLink(), headers = self.HDR, stream = True)

		if r.status_code == 200:
			# download started 
			with open(f"{title}.mp4", 'wb') as f:
				total_length = int(r.headers.get('content-length'))
				for chunk in r.iter_content(chunk_size = 1024*1024):
					if chunk: 
						f.write(chunk)
						f.flush()
				else:
					return True
		return False

### ERRORS ######

class ServerNotSupported(Exception):
	def __init__(self, server):
		self.server = server
		self.message = f"Il server {server} non è supportato."
		super().__init__(self.message)

class AnimeNotAvailable(Exception):
	def __init__(self, animeName=''):
		self.anime = animeName
		self.message = f"L'anime '{animeName}' non è acora disponibile."
		super().__init__(self.message)