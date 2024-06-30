from indicnlp.tokenize import sentence_tokenize
import torch
from IndicTransTokenizer import IndicProcessor
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from nltk.tokenize import sent_tokenize


class Translator:
    def __init__(self):
        self.ip = IndicProcessor(inference=True)

    def translate(self, text, src_lang, tgt_lang):
        if src_lang == tgt_lang:
            return text
        
        if src_lang == "eng_Latn":
            model_name = "ai4bharat/indictrans2-en-indic-1B"
        elif tgt_lang == "eng_Latn":
            model_name = "ai4bharat/indictrans2-indic-en-1B"
        else:
            model_name = "ai4bharat/indictrans2-indic-indic-1B"
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name, trust_remote_code=True)



        if src_lang == "eng_Latn":
            sentences = sent_tokenize(text)
        else:
            sentences = sentence_tokenize.sentence_split(text, lang=src_lang.split('_')[0])
        batch = self.ip.preprocess_batch(
            sentences,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
        )

        DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(DEVICE)

        inputs = self.tokenizer(
            batch,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(DEVICE)

        # Generate translations using the model
        with torch.no_grad():
            generated_tokens = self.model.generate(
                **inputs,
                use_cache=True,
                min_length=0,
                max_length=256,
                num_beams=5,
                num_return_sequences=1,
            )

        # Decode the generated tokens into text
        with self.tokenizer.as_target_tokenizer():
            generated_tokens = self.tokenizer.batch_decode(
                generated_tokens.detach().cpu().tolist(),
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )

        # Postprocess the translations, including entity replacement
        translations = self.ip.postprocess_batch(generated_tokens, lang=tgt_lang)
        translated_text =  ' '.join(translations)
        
        return translated_text


