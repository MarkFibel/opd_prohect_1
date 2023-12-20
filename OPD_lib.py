import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import whisper
import numpy as np
import math
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.signal import argrelextrema
import yt_dlp
import openai


class _GPTRequest:
    def __init__(self):
        file_secret = open('vse_secret.txt')
        openai.api_key = file_secret.readline()
        openai.base_url = file_secret.readline()

    def request_to_gpt(self, prompt) -> str:
        messages = []
        messages.append({"role": "user", "content": prompt})
        response_big = openai.chat.completions.create(
            model="openai/gpt-3.5-turbo-1106",
            messages=messages,
            temperature=0.7,
            n=1,
            max_tokens=len(prompt.split()) + 10,
        )
        response = response_big.choices[0].message.content
        return response


class _SpeechRecognize:
    def __init__(self, chat_id):
        self.__chat_id = chat_id
        self.speech_model = whisper.load_model('tiny')


    def do_split_paragrahes(self, text_4_split):
        text = text_4_split
        model = SentenceTransformer('all-mpnet-base-v2')
        sentences = text.split('. ')
        embeddings = model.encode(sentences)

        similarities = cosine_similarity(embeddings)

        def rev_sigmoid(x: float) -> float:
            return (1 / (1 + math.exp(0.5 * x)))

        def activate_similarities(similarities: np.array, p_size=10) -> np.array:
            """ Функция возвращает список взвешенных сумм активированных сходств предложений
        Аргументы:
                similarities (numpy array): это должна быть квадратная матрица, где каждое предложение соответствует другому согласно мере подобия.
                p_size (int): количество предложений используется для расчета взвешенной суммы
        Возврат:
                list: список взвешенных сумм
            """
            x = np.linspace(-10, 10, p_size)
            y = np.vectorize(rev_sigmoid)
            activation_weights = np.pad(y(x), (0, similarities.shape[0] - p_size))
            diagonals = [similarities.diagonal(each) for each in range(0, similarities.shape[0])]
            diagonals = [np.pad(each, (0, similarities.shape[0] - len(each))) for each in diagonals]
            diagonals = np.stack(diagonals)
            diagonals = diagonals * activation_weights.reshape(-1, 1)
            activated_similarities = np.sum(diagonals, axis=0)
            return activated_similarities

        activated_similarities = activate_similarities(similarities, p_size=5)
        minmimas = argrelextrema(activated_similarities, np.less,
                                 order=2)

        sentece_length = [len(each) for each in sentences]
        long = np.mean(sentece_length) + np.std(sentece_length) * 2
        short = np.mean(sentece_length) - np.std(sentece_length) * 2
        text = ''
        for each in sentences:
            if len(each) > long:
                comma_splitted = each.replace(',', '.')
            else:
                text += f'{each}. '
        sentences = text.split('. ')
        text = ''
        for each in sentences:
            if len(each) < short:
                text += f'{each} '
            else:
                text += f'{each}. '

        split_points = [each for each in minmimas[0]]
        text = ''
        for num, each in enumerate(sentences):
            if num in split_points:
                text += f'\n {each}. '
            else:
                text += f'{each}. '

        return text

    def speech_recognition(self):
        result = self.speech_model.transcribe(f'{self.__chat_id}.mp3')

        text_with_time = []
        list_sent_time = result['segments']
        for item in list_sent_time:
            text_with_time.append(f'''{item['start']} {item['text']}''')

        text_without_time = result['text']
        paragraphs = self.do_split_paragrahes(text_without_time)

        out_paragraphs_time = {}

        for paragraph in paragraphs.split('\n'):
            for line in text_with_time:
                time, word = line.split('  ')
                minute, second = int(float(time)) // 60, int(float(time)) % 60
                time_code = f'{minute // 10}{minute % 10}:{second // 10}{second % 10}'
                if word in paragraph:
                    out_paragraphs_time[time_code] = paragraph
                    break
        return [out_paragraphs_time, paragraphs]


class _ScribeVideo:
    def __init__(self, chat_id):
        self.__chat_id = chat_id
        self.gpt_model = _GPTRequest()

    def do_scribe(self, texts_recognize: list):
        """
        Делает Расшивроку аудио с таймкодами
        :return:
        """
        with open(f'scribe_video_{self.__chat_id}.txt', 'w') as file:
            file.write('')
        time_paragraph, text = texts_recognize
        text = text.split('\n')
        topics = []

        for paragraph in text:
            prompt = f'Напиши, пожалуйста, тему этого абзаца: {paragraph}'
            answer = self.gpt_model.request_to_gpt(prompt)
            topics.append(answer)

        counter = 1
        for time_code in time_paragraph.keys():
            with open(f'scribe_video_{self.__chat_id}.txt', 'a') as file:
                file.write(f'{time_code} {topics[counter - 1]}\n')
            counter += 1


class _ShortDescription:
    def __init__(self, chat_id):
        self.__chat_id = chat_id
        self.gpt_model = _GPTRequest()

    @staticmethod
    def split_chunks(max_tokens: int, text_recognize: list) -> list:
        text = text_recognize[1].split('\n')
        chunks, chunk = [], ''
        chunk_tokens = 0
        for paragraph in text:
            quant_tokens = len(paragraph.split())
            if chunk_tokens + quant_tokens < max_tokens:
                if quant_tokens != 0:
                    chunk += paragraph
                    chunk_tokens += quant_tokens
            elif chunk_tokens + quant_tokens > max_tokens:
                if quant_tokens != 0:
                    chunks.append(chunk)
                    chunk = paragraph
                    chunk_tokens = quant_tokens
        chunks.append(chunk)
        return chunks

    def request_2_gpt(self, prompt) -> str:
        return self.gpt_model.request_to_gpt(prompt)

    def short(self, max_tokens: int, text_recognize: list):
        chunks = self.split_chunks(max_tokens, text_recognize)

        short_desc = ''
        for chunk in chunks:
            prompt = f'Сократи, пожалуйста, этот текст: {chunk}'
            short_desc += self.request_2_gpt(prompt)

        with open(f'short_description_{self.__chat_id}.txt', 'w') as file:
            file.write(short_desc)


class ChatBotFunc:
    def __init__(self):
        self.url = None
        self.__chat_id = None
        self.__speech = None
        self.__short = None
        self.__scribe = None
        self.__recognition = None
        self.__max_tokens = 16_000

    def get_url(self, url: str):
        self.url = url

    def get_chat_id(self, chat_id: str):
        self.__chat_id = chat_id
        self.__speech = _SpeechRecognize(chat_id)
        self.__short = _ShortDescription(chat_id)
        self.__scribe = _ScribeVideo(chat_id)

    def download_audio(self):
        '''
        download audio from YouTube
        :return:
        '''
        ydl_opts = {'format': 'bestaudio/best',
                        'outtmpl': f'{self.__chat_id}',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'postprocessor_args': [
                            '-ar', '16000'
                        ],
                        'prefer_ffmpeg': True,
                        'keepvideo': False
                        }
        url = [self.url]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(url)
        self.__recognition = self.__speech.speech_recognition()

    def do_scribe(self):
        self.__scribe.do_scribe(self.__recognition)

    def do_short(self):
        self.__short.short(self.__max_tokens, self.__recognition)
