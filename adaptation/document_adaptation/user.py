class User():
    ''' User interface '''
    def __init__(self, user_profile):
        self.tastes = []
        self.expertise_level = 1  # enum from ["child","novice","knowledgeable","expert"]
        self.language = 'en'
        self.tastes_embedded = {}
        if 'tastes' in user_profile:
            self.tastes = user_profile['tastes']
        if 'expertiseLevel' in user_profile:
            self.expertise_level = int(user_profile['expertiseLevel']) 
        if 'language' in user_profile:
            self.language = user_profile['language']
    
    def embed_tastes(self, embedder):
        if self.tastes:
            for taste in self.tastes:
                self.tastes_embedded[taste] = embedder.embed(taste)
        print(self.tastes_embedded)

