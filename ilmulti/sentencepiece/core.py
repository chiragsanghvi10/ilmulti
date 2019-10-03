import os
import sentencepiece as spm
from warnings import warn
from ilmulti.utils import language_token, detect_lang
from collections import Counter

class LazySPM:
    def __init__(self, path, lang, units):
        self.path = path
        self.lang = lang
        self.units = units
        self.build_vocabulary()
        self.load_model()

    def load_model(self):
        model_file = '{lang}.{units}.model'.format(lang=self.lang, units=self.units)
        model_path = os.path.join(self.path, model_file)
        self.model = spm.SentencePieceProcessor()
        self.model.load(model_path)

    def build_vocabulary(self):
        vocab_file = '{}.{}.vocab'.format(self.lang, self.units)
        vocab_path = os.path.join(self.path, vocab_file)
        self.vocab = set()
        with open(vocab_path) as fp:
            for line in fp:
                word, _ = line.strip().split()
                self.vocab.add(word)

    def __call__(self, text):
        tokens = self.model.EncodeAsPieces(text)
        # Clean unwanted tokens
        clean = lambda x: x in self.vocab
        # print(self.lang, self.units, tokens)
        tokens = list(filter(clean, tokens))
        return tokens

class SentencePieceTokenizer:
    def __init__(self, model_path=None, units=[2000,4000]):
        if model_path is None:
            cdir = os.path.abspath(os.path.dirname(__file__))
            model_path = os.path.join(cdir, 'models')

        self.model_path = model_path
        self.tokenizer = {}
        self.units = units
        self.load_models()

    def load_models(self):
        from itertools import chain
        files = os.listdir(self.model_path)
        model_files = filter(lambda f: ".model" in f, files)
        model_files = filter(lambda f: "{}".format(self.units[0]) in f, files)
        models = filter(lambda f: "{}".format(self.units[1]) in f, files)
        model_files = chain(model_files,models)
        for model_file in model_files:
            lang, units, ext = model_file.split('.')
            units = int(units)
            print(lang, units, ext)
            self.tokenizer[(lang, units)] = LazySPM(self.model_path, lang, units)

    def __call__(self, text, lang=None):
        if lang is None:
            export = detect_lang(text, 'segmented')
            tokens, langs = [], []
            for segment, lang in export:
                tokenizer = self.get_tokenizer(lang)
                segment_tokens = tokenizer(segment)
                tokens.extend(segment_tokens)
                langs.append(lang)

            lang, *_ = Counter(langs).most_common(1)
            return (lang, tokens)

        tokenizer = self.get_tokenizer(lang)
        tokens = tokenizer(text)
        return (lang, tokens)

    def detokenize(self, value):
        SPM_SYMBOL = '▁'
        value = value.replace(' ', '')
        value = value.replace(SPM_SYMBOL, ' ')
        if not value:
            return ''
        if value[0] == ' ':
            value = value[1:]
        return value


    def dictionary(self):
        from fairseq.data.dictionary import Dictionary
        dictionary = Dictionary()

        vocab = set()

        # Add language_tokens
        langs, _ = list(zip(*self.tokenizer.keys()))
        langs = list(map(language_token, langs))
        vocab = vocab.union(set(langs))

        for key in self.tokenizer:
            tokenizer_vocab = self.tokenizer[key].vocab
            vocab = vocab.union(tokenizer_vocab)
            # print("Vocab tokens: ", key, len(tokenizer_vocab))

        vocab = sorted(list(vocab))
        for word in vocab:
            dictionary.add_symbol(word)

        # print("Vocab tokens:", len(vocab))
        # print("Non-control:", len(vocab) - len(langs))

        return dictionary

    def get_tokenizer(self, lang):
        if lang in ['gu','or','mr','pa']: #2K vocab switch
            self.units = self.units[0]
        else:
            self.units = self.units[1]   
        default = self.tokenizer[("en", self.units)]
        return self.tokenizer.get((lang, self.units), default)

if __name__ == '__main__':
    sp = SentencePieceTokenizer()
    s = sp("Hello world!",lang='en')
    print(sp.dictionary())
    print(s)
