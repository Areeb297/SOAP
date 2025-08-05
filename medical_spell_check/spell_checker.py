# Medical Spell Checker
"""
This module provides the main spell checking functionality for medical terms
"""

from textblob import TextBlob
from fuzzywuzzy import fuzz, process
import re
from typing import List, Dict, Tuple, Optional
from .medical_dictionary import MedicalDictionary
from .snomed_api import SnomedAPI
from .dynamic_medicine_list import DynamicMedicineList
from .medical_nlp import MedicalNLP
import openai
from openai import OpenAI
import os

class MedicalSpellChecker:
    def __init__(self):
        self.medical_dict = MedicalDictionary()
        self.snomed_api = SnomedAPI()
        self.dynamic_list = DynamicMedicineList()
        
        # Initialize Medical NLP (replaces LLM for better performance)
        self.medical_nlp = MedicalNLP()
        
        # Initialize OpenAI client for LLM-based classification (fallback only)
        try:
            self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.use_llm = bool(os.getenv("OPENAI_API_KEY"))
        except:
            self.llm_client = None
            self.use_llm = False
        
        # Configuration flags
        self.use_snomed_api = True  # Can be disabled for LLM-only mode
        self.llm_only_mode = False  # Flag to bypass SNOMED entirely
        
        # Enhanced medical term patterns for faster detection
        self.medical_patterns = [
            # Medications (common drug suffixes)
            r'\b\w+(?:in|ol|ide|ate|ine|one|pam|lol|pril|tidine|zole|mycin|illin|profen|fen|dine)\b',
            # Medical conditions (common condition suffixes)
            r'\b\w+(?:itis|osis|emia|oma|pathy|algia|emia|osis|oma|cele|rrhagia|rrhea)\b',
            # Common medical abbreviations
            r'\b(?:BP|HR|RR|O2|CT|MRI|ECG|EKG|CBC|BMP|CMP|PT|INR|CXR|EKG|IV|PO|PRN|QID|TID|BID|QD)\b',
            # Dosage patterns
            r'\b\d+\s*(?:mg|mcg|g|ml|cc|units?|IU|mEq|mmol)\b',
            # Common medical prefixes
            r'\b(?:cardio|neuro|gastro|hepato|nephro|pulmo|dermo|endo|exo|hyper|hypo|anti|pro|pre|post)\w*\b',
            # Specific medical terms
            r'\b(?:diabetes|hypertension|asthma|pneumonia|bronchitis|sinusitis|migraine|arthritis|depression|anxiety|fever|cough|headache|nausea|vomiting|pain|swelling|bleeding|infection|inflammation)\b',
            # Drug names (common patterns)
            r'\b(?:aspirin|ibuprofen|acetaminophen|metformin|lisinopril|atorvastatin|omeprazole|simvastatin|amoxicillin|levothyroxine|metoprolol|amlodipine|losartan|hydrochlorothiazide|furosemide|warfarin|insulin|morphine|oxycodone|tramadol)\b'
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.medical_patterns]
        
        # Comprehensive skip words - common English words that are not medical terms
        self.skip_words = {
            # Articles, conjunctions, prepositions
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
            
            # Verbs
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'can', 'must', 'shall', 'ought', 'need', 'dare', 'used', 'want', 'like',
            'know', 'think', 'see', 'get', 'go', 'come', 'take', 'give', 'make',
            'put', 'say', 'tell', 'ask', 'help', 'try', 'keep', 'let', 'seem',
            'turn', 'start', 'show', 'hear', 'play', 'run', 'move', 'live', 'believe',
            'bring', 'happen', 'write', 'provide', 'sit', 'stand', 'lose', 'pay',
            'meet', 'include', 'continue', 'set', 'learn', 'change', 'lead', 'understand',
            'watch', 'follow', 'stop', 'create', 'speak', 'read', 'allow', 'add',
            'spend', 'grow', 'open', 'walk', 'win', 'offer', 'remember', 'love',
            'consider', 'appear', 'buy', 'wait', 'serve', 'die', 'send', 'expect',
            'build', 'stay', 'fall', 'cut', 'reach', 'kill', 'remain', 'suggest',
            'raise', 'pass', 'sell', 'require', 'report', 'decide', 'pull',
            
            # Pronouns
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'mine', 'yours', 'his', 'hers', 'ours', 'theirs', 'myself', 'yourself',
            'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves',
            'this', 'that', 'these', 'those', 'who', 'whom', 'whose', 'which', 'what',
            
            # Common adjectives/adverbs
            'good', 'bad', 'big', 'small', 'large', 'little', 'long', 'short',
            'high', 'low', 'hot', 'cold', 'warm', 'cool', 'new', 'old', 'young',
            'great', 'important', 'public', 'same', 'different', 'able', 'ready',
            'possible', 'available', 'free', 'sure', 'common', 'whole', 'clear',
            'easy', 'hard', 'simple', 'difficult', 'early', 'late', 'strong', 'weak',
            'nice', 'fine', 'ok', 'okay', 'right', 'wrong', 'true', 'false',
            'real', 'full', 'empty', 'clean', 'dirty', 'safe', 'dangerous', 'happy',
            'sad', 'angry', 'afraid', 'surprised', 'excited', 'tired', 'hungry',
            'thirsty', 'sick', 'healthy', 'rich', 'poor', 'smart', 'stupid',
            'beautiful', 'ugly', 'interesting', 'boring', 'funny', 'serious',
            'quiet', 'loud', 'fast', 'slow', 'careful', 'careless', 'kind', 'mean',
            'friendly', 'unfriendly', 'polite', 'rude', 'honest', 'dishonest',
            'very', 'quite', 'rather', 'pretty', 'really', 'actually', 'just',
            'only', 'even', 'also', 'too', 'so', 'such', 'much', 'many', 'few',
            'more', 'most', 'less', 'least', 'enough', 'almost', 'always', 'never',
            'sometimes', 'often', 'usually', 'rarely', 'hardly', 'nearly', 'probably',
            'certainly', 'perhaps', 'maybe', 'definitely', 'absolutely', 'completely',
            'totally', 'exactly', 'directly', 'immediately', 'quickly', 'slowly',
            'carefully', 'easily', 'simply', 'clearly', 'obviously', 'especially',
            'particularly', 'generally', 'usually', 'normally', 'typically',
            
            # Common nouns (non-medical)
            'time', 'day', 'night', 'morning', 'evening', 'afternoon', 'week', 'month',
            'year', 'today', 'tomorrow', 'yesterday', 'hour', 'minute', 'second',
            'moment', 'while', 'period', 'season', 'spring', 'summer', 'fall', 'winter',
            'home', 'house', 'room', 'kitchen', 'bedroom', 'bathroom', 'office',
            'school', 'store', 'shop', 'restaurant', 'hotel', 'hospital', 'church',
            'park', 'street', 'road', 'car', 'bus', 'train', 'plane', 'bike',
            'boat', 'ship', 'phone', 'computer', 'internet', 'email', 'website',
            'book', 'paper', 'pen', 'pencil', 'table', 'chair', 'door', 'window',
            'wall', 'floor', 'ceiling', 'light', 'lamp', 'bed', 'couch', 'tv',
            'radio', 'music', 'movie', 'game', 'sport', 'ball', 'team', 'player',
            'money', 'dollar', 'cent', 'price', 'cost', 'job', 'work', 'business',
            'company', 'boss', 'employee', 'worker', 'customer', 'client', 'service',
            'product', 'item', 'thing', 'stuff', 'object', 'tool', 'machine',
            'equipment', 'device', 'system', 'method', 'way', 'process', 'step',
            'part', 'piece', 'section', 'area', 'place', 'location', 'position',
            'point', 'line', 'circle', 'square', 'triangle', 'shape', 'form',
            'size', 'length', 'width', 'height', 'weight', 'speed', 'distance',
            'number', 'amount', 'quantity', 'level', 'degree', 'rate', 'percent',
            'food', 'water', 'drink', 'coffee', 'tea', 'milk', 'juice', 'beer',
            'wine', 'alcohol', 'bread', 'meat', 'fish', 'chicken', 'beef', 'pork',
            'cheese', 'egg', 'fruit', 'apple', 'orange', 'banana', 'vegetable',
            'potato', 'tomato', 'onion', 'rice', 'pasta', 'pizza', 'sandwich',
            'soup', 'salad', 'cake', 'cookie', 'ice', 'cream', 'sugar', 'salt',
            'people', 'person', 'man', 'woman', 'child', 'baby', 'boy', 'girl',
            'family', 'parent', 'father', 'mother', 'son', 'daughter', 'brother',
            'sister', 'husband', 'wife', 'friend', 'neighbor', 'guest', 'visitor',
            'name', 'age', 'birthday', 'address', 'phone', 'email', 'country',
            'city', 'state', 'world', 'earth', 'sky', 'sun', 'moon', 'star',
            'cloud', 'rain', 'snow', 'wind', 'weather', 'temperature', 'season',
            'color', 'red', 'blue', 'green', 'yellow', 'black', 'white', 'brown',
            'orange', 'purple', 'pink', 'gray', 'silver', 'gold',
            
            # Medical context words that should NOT be flagged for spelling
            'preventing', 'prevention', 'routine', 'treatment', 'treatments', 'prescribed', 
            'prescribing', 'medicine', 'medicines', 'medication', 'medications', 'therapy',
            'therapies', 'procedure', 'procedures', 'diagnosis', 'diagnoses', 'symptom',
            'symptoms', 'condition', 'conditions', 'patient', 'patients', 'doctor', 'doctors',
            'physician', 'physicians', 'nurse', 'nurses', 'hospital', 'clinic', 'medical',
            'clinical', 'health', 'healthcare', 'examination', 'exam', 'visit', 'appointment',
            'follow', 'followup', 'follow-up', 'checkup', 'check-up', 'monitoring', 'monitor',
            'screening', 'tested', 'testing', 'results', 'finding', 'findings', 'normal',
            'abnormal', 'positive', 'negative', 'elevated', 'decreased', 'increased', 'stable',
            'chronic', 'acute', 'severe', 'mild', 'moderate', 'recent', 'history', 'family',
            'personal', 'social', 'allergic', 'allergy', 'allergies', 'reaction', 'reactions',
            'dosage', 'dose', 'doses', 'daily', 'weekly', 'monthly', 'twice', 'once', 'times',
            'morning', 'evening', 'night', 'bedtime', 'meals', 'before', 'after', 'with', 'without',
            'take', 'taking', 'taken', 'discontinue', 'continue', 'start', 'stop', 'increase',
            'decrease', 'adjust', 'change', 'switch', 'replace', 'substitute', 'alternative',
            'recommend', 'recommended', 'suggest', 'suggested', 'advise', 'advised', 'instruct',
            'instructed', 'explain', 'explained', 'discuss', 'discussed', 'review', 'reviewed',
            'assess', 'assessed', 'evaluate', 'evaluated', 'examine', 'examined', 'observe',
            'observed', 'report', 'reported', 'complain', 'complained', 'concern', 'concerned',
            'worry', 'worried', 'improve', 'improved', 'worsen', 'worsened', 'progress',
            'progressed', 'recover', 'recovered', 'healing', 'healed', 'response', 'responded',
            'effective', 'ineffective', 'helpful', 'unhelpful', 'beneficial', 'harmful',
            'side', 'effects', 'adverse', 'contraindication', 'indication', 'precaution',
            'warning', 'caution', 'safety', 'risk', 'benefit', 'outcome', 'prognosis',
            
            # Words that commonly get flagged incorrectly
            'online', 'decide', 'provide', 'provided', 'service', 'services',
            'include', 'including', 'information', 'system', 'systems', 'process',
            'processes', 'method', 'methods', 'way', 'ways', 'type', 'types',
            'kind', 'kinds', 'form', 'forms', 'part', 'parts', 'section', 'sections',
            'area', 'areas', 'place', 'places', 'time', 'times', 'case', 'cases',
            'example', 'examples', 'problem', 'problems', 'question', 'questions',
            'answer', 'answers', 'solution', 'solutions', 'result', 'results',
            'effect', 'effects', 'cause', 'causes', 'reason', 'reasons', 'purpose',
            'purposes', 'goal', 'goals', 'plan', 'plans', 'idea', 'ideas',
            'thought', 'thoughts', 'opinion', 'opinions', 'view', 'views',
            'point', 'points', 'fact', 'facts', 'detail', 'details', 'item',
            'items', 'list', 'lists', 'order', 'orders', 'number', 'numbers',
            'amount', 'amounts', 'level', 'levels', 'rate', 'rates', 'value',
            'values', 'price', 'prices', 'cost', 'costs', 'benefit', 'benefits',
            'advantage', 'advantages', 'disadvantage', 'disadvantages', 'feature',
            'features', 'option', 'options', 'choice', 'choices', 'decision',
            'decisions', 'action', 'actions', 'activity', 'activities', 'event',
            'events', 'situation', 'situations', 'condition', 'conditions',
            'state', 'states', 'status', 'position', 'positions', 'role', 'roles',
            'function', 'functions', 'job', 'jobs', 'task', 'tasks', 'duty', 'duties',
            'responsibility', 'responsibilities', 'opportunity', 'opportunities',
            'chance', 'chances', 'possibility', 'possibilities', 'ability',
            'abilities', 'skill', 'skills', 'knowledge', 'experience', 'background',
            'education', 'training', 'learning', 'study', 'research', 'test',
            'tests', 'exam', 'exams', 'grade', 'grades', 'score', 'scores',
            'mark', 'marks', 'record', 'records', 'report', 'reports', 'document',
            'documents', 'file', 'files', 'page', 'pages', 'line', 'lines',
            'word', 'words', 'sentence', 'sentences', 'paragraph', 'paragraphs',
            'text', 'texts', 'message', 'messages', 'letter', 'letters', 'note',
            'notes', 'comment', 'comments', 'remark', 'remarks', 'statement',
            'statements', 'explanation', 'explanations', 'description', 'descriptions',
            'definition', 'definitions', 'instruction', 'instructions', 'direction',
            'directions', 'rule', 'rules', 'law', 'laws', 'regulation', 'regulations',
            'policy', 'policies', 'procedure', 'procedures', 'standard', 'standards',
            'requirement', 'requirements', 'specification', 'specifications',
            'guideline', 'guidelines', 'principle', 'principles', 'theory',
            'theories', 'concept', 'concepts', 'model', 'models', 'pattern',
            'patterns', 'structure', 'structures', 'design', 'designs', 'style',
            'styles', 'fashion', 'trend', 'trends', 'culture', 'society',
            'community', 'group', 'groups', 'team', 'teams', 'organization',
            'organizations', 'company', 'companies', 'business', 'businesses',
            'industry', 'industries', 'market', 'markets', 'economy', 'economics',
            'politics', 'government', 'authority', 'authorities', 'power', 'powers',
            'control', 'influence', 'leadership', 'management', 'administration',
            'operation', 'operations', 'production', 'manufacturing', 'development',
            'improvement', 'progress', 'growth', 'change', 'changes', 'difference',
            'differences', 'comparison', 'comparisons', 'contrast', 'contrasts',
            'relationship', 'relationships', 'connection', 'connections', 'link',
            'links', 'association', 'associations', 'partnership', 'partnerships',
            'cooperation', 'collaboration', 'communication', 'conversation',
            'conversations', 'discussion', 'discussions', 'meeting', 'meetings',
            'conference', 'conferences', 'presentation', 'presentations', 'speech',
            'speeches', 'talk', 'talks', 'interview', 'interviews', 'negotiation',
            'negotiations', 'agreement', 'agreements', 'contract', 'contracts',
            'deal', 'deals', 'offer', 'offers', 'proposal', 'proposals', 'suggestion',
            'suggestions', 'recommendation', 'recommendations', 'advice', 'tip',
            'tips', 'hint', 'hints', 'clue', 'clues', 'sign', 'signs', 'signal',
            'signals', 'warning', 'warnings', 'alarm', 'alarms', 'emergency',
            'emergencies', 'crisis', 'danger', 'dangers', 'risk', 'risks',
            'threat', 'threats', 'challenge', 'challenges', 'difficulty',
            'difficulties', 'trouble', 'troubles', 'issue', 'issues', 'concern',
            'concerns', 'worry', 'worries', 'fear', 'fears', 'anxiety', 'stress',
            'pressure', 'tension', 'conflict', 'conflicts', 'dispute', 'disputes',
            'argument', 'arguments', 'fight', 'fights', 'war', 'wars', 'battle',
            'battles', 'competition', 'competitions', 'contest', 'contests',
            'game', 'games', 'match', 'matches', 'race', 'races', 'tournament',
            'tournaments', 'championship', 'championships', 'victory', 'victories',
            'win', 'wins', 'success', 'failure', 'failures', 'mistake', 'mistakes',
            'error', 'errors', 'fault', 'faults', 'blame', 'criticism', 'praise',
            'compliment', 'compliments', 'reward', 'rewards', 'prize', 'prizes',
            'gift', 'gifts', 'present', 'presents', 'surprise', 'surprises',
            'celebration', 'celebrations', 'party', 'parties', 'festival',
            'festivals', 'holiday', 'holidays', 'vacation', 'vacations', 'trip',
            'trips', 'journey', 'journeys', 'travel', 'adventure', 'adventures',
            'experience', 'experiences', 'memory', 'memories', 'dream', 'dreams',
            'hope', 'hopes', 'wish', 'wishes', 'desire', 'desires', 'need',
            'needs', 'want', 'wants', 'interest', 'interests', 'hobby', 'hobbies',
            
            # Numbers and units (non-medical)
            'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
            'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
            'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty',
            'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety', 'hundred',
            'thousand', 'million', 'billion', 'trillion', 'first', 'second', 'third',
            'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth',
            'last', 'next', 'previous', 'following', 'final', 'initial', 'original',
            'main', 'primary', 'secondary', 'basic', 'advanced', 'professional',
            'personal', 'private', 'public', 'general', 'specific', 'special',
            'particular', 'individual', 'single', 'double', 'triple', 'multiple',
            'several', 'various', 'different', 'similar', 'same', 'other', 'another',
            'additional', 'extra', 'more', 'less', 'fewer', 'most', 'least',
            'all', 'some', 'any', 'every', 'each', 'both', 'either', 'neither',
            'none', 'nothing', 'something', 'anything', 'everything', 'somewhere',
            'anywhere', 'everywhere', 'nowhere', 'someone', 'anyone', 'everyone',
            'no-one', 'nobody', 'somebody', 'anybody', 'everybody'
        }
    
    def is_medical_term_llm(self, term: str) -> bool:
        """
        Use LLM to determine if a term is medical-related
        
        Args:
            term: The term to check
            
        Returns:
            True if the term is medical-related, False otherwise
        """
        if not self.use_llm or not self.llm_client:
            return False
            
        # Cache results to avoid repeated API calls
        if not hasattr(self, '_llm_cache'):
            self._llm_cache = {}
            
        term_lower = term.lower()
        if term_lower in self._llm_cache:
            return self._llm_cache[term_lower]
        
        try:
            prompt = f"""Is the word "{term}" a medical term? This includes:
- Medications/drugs (e.g., aspirin, metformin)
- Medical conditions/diseases (e.g., diabetes, hypertension) 
- Medical procedures (e.g., surgery, biopsy)
- Body parts/anatomy (e.g., heart, lung)
- Medical equipment/devices
- Medical symptoms (e.g., nausea, fatigue)
- Medical specialties (e.g., cardiology)

Answer only "yes" or "no"."""

            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=5
            )
            
            answer = response.choices[0].message.content.lower().strip()
            is_medical = answer.startswith('yes')
            
            # Cache the result
            self._llm_cache[term_lower] = is_medical
            return is_medical
            
        except Exception as e:
            print(f"LLM classification error for term '{term}': {e}")
            return False
    
    def identify_medical_terms_llm(self, text: str) -> List[Tuple[str, int, int, str]]:
        """
        Use LLM to identify ONLY actual medical terms in text
        
        Args:
            text: The text to analyze
            
        Returns:
            List of tuples (term, start_pos, end_pos, category)
        """
        if not self.use_llm or not self.llm_client:
            print("LLM not available, using NLP fallback")
            return self.identify_medical_terms_nlp(text)
        
        print(f"Using LLM to identify medical terms in text (length: {len(text)} chars)")
        try:
            prompt = f"""Analyze this medical transcript and identify ONLY the actual medical terms. 

Include ONLY:
- Medical conditions/diseases (diabetes, mellitus, hyperglycemia, hypertension, pneumonia, asthma)
- Medications/drugs (metformin, aspirin, insulin, lisinopril, atorvastatin)
- Medical procedures (surgery, biopsy, X-ray, MRI, CT scan, echocardiogram)
- Laboratory tests (HbA1c, A1C, CBC, blood sugar, glucose, cholesterol, creatinine)  
- Body parts/anatomy (heart, liver, kidney, abdomen, chest)
- Medical symptoms when specific (chest pain, shortness of breath, nausea, headache)
- Dosages with medical context (500mg, twice daily when referring to medication)
- Medical terminology components (mellitus in "diabetes mellitus", hyperglycemic, hypoglycemic)

EXCLUDE:
- Common words, greetings, names (Good morning, Khan, Dr. Smith, patient names)
- Time phrases (last week, this morning, a month ago, today, yesterday)  
- General conversation (How are you, I'm okay, Thank you, Hello, Goodbye)
- Non-medical descriptors (tired, okay, fine, better, worse, little, much)
- Articles and prepositions (the, a, an, in, on, at, with, for)

IMPORTANT: Include diabetes-related terms like "diabetes", "mellitus", "hyperglycemia", "blood sugar", "glucose", "HbA1c", "A1C".

Text: "{text}"

Format your response as JSON with this exact structure:
{{"medical_terms": [{{"term": "diabetes", "category": "condition"}}, {{"term": "mellitus", "category": "condition"}}, {{"term": "HbA1c", "category": "test"}}]}}

Return only the JSON, no other text."""

            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content.strip()
            
            # Clean up markdown code blocks if present
            import re
            import json
            
            # Remove markdown code block markers
            result = re.sub(r'^```json\s*', '', result, flags=re.MULTILINE)
            result = re.sub(r'^```\s*$', '', result, flags=re.MULTILINE)
            result = result.strip()
            
            # Parse JSON response
            try:
                data = json.loads(result)
                llm_terms = data.get("medical_terms", [])
                print(f"Successfully parsed LLM response: {len(llm_terms)} terms found")
            except json.JSONDecodeError:
                print(f"LLM returned invalid JSON after cleanup: {result[:200]}...")
                print("Falling back to NLP method")
                return self.identify_medical_terms_nlp(text)
            
            # Find positions of LLM-identified terms in the text
            medical_terms = []
            text_lower = text.lower()
            
            for term_data in llm_terms:
                term = term_data.get("term", "")
                category = term_data.get("category", "medical")
                
                if not term:
                    continue
                    
                # Find all occurrences of this term in the text
                term_lower = term.lower()
                start_pos = 0
                
                while True:
                    pos = text_lower.find(term_lower, start_pos)
                    if pos == -1:
                        break
                    
                    # Check if it's a whole word (not part of another word)
                    if (pos == 0 or not text[pos-1].isalnum()) and \
                       (pos + len(term) == len(text) or not text[pos + len(term)].isalnum()):
                        end_pos = pos + len(term)
                        medical_terms.append((text[pos:end_pos], pos, end_pos, category))
                    
                    start_pos = pos + 1
            
            # Sort by position and remove duplicates
            medical_terms = list(set(medical_terms))  # Remove duplicates
            medical_terms.sort(key=lambda x: x[1])  # Sort by start position
            
            print(f"LLM identified {len(medical_terms)} medical terms: {[term[0] for term in medical_terms]}")
            return medical_terms
            
        except Exception as e:
            print(f"LLM medical term identification error: {e}")
            print("Falling back to NLP method due to LLM error")
            return self.identify_medical_terms_nlp(text)
    
    def identify_medical_terms_nlp(self, text: str) -> List[Tuple[str, int, int, str]]:
        """
        Fallback: Identify potential medical terms using NLP (when LLM unavailable)
        
        Args:
            text: The text to analyze
            
        Returns:
            List of tuples (term, start_pos, end_pos, category)
        """
        medical_terms = []
        
        print("Using NLP fallback for medical term identification")
        
        # Conservative skip words for common terms that should never be highlighted
        conservative_skip_words = {
            'good', 'morning', 'afternoon', 'evening', 'night', 'hello', 'hi', 'bye', 'goodbye',
            'thank', 'thanks', 'please', 'okay', 'ok', 'yes', 'no', 'sure', 'fine', 'well',
            'today', 'yesterday', 'tomorrow', 'week', 'month', 'year', 'day', 'time',
            'last', 'next', 'this', 'that', 'these', 'those', 'here', 'there', 'where',
            'doctor', 'patient', 'mr', 'mrs', 'ms', 'dr', 'khan', 'smith', 'john', 'mary',
            'feel', 'feeling', 'felt', 'tired', 'better', 'worse', 'little', 'much', 'more',
            'take', 'taking', 'taken', 'give', 'giving', 'come', 'coming', 'go', 'going'
        }
        
        # Use medical NLP for primary detection (fast and accurate)
        if self.medical_nlp.is_available():
            try:
                nlp_entities = self.medical_nlp.identify_medical_entities(text)
                for entity_text, start, end, label, category in nlp_entities:
                    # Skip common words and obvious non-medical terms
                    entity_lower = entity_text.lower()
                    if (entity_lower not in conservative_skip_words and 
                        len(entity_text) > 2 and  # Skip very short terms
                        not entity_lower.startswith(('mr', 'mrs', 'ms', 'dr')) and  # Skip titles
                        entity_text.replace(' ', '').isalpha()):  # Skip numbers-only terms
                        medical_terms.append((entity_text, start, end, category))
                        print(f"NLP fallback identified: {entity_text} ({category})")
            except Exception as e:
                print(f"Medical NLP error: {e}")
        
        # Only return very conservative medical terms
        print(f"NLP fallback found {len(medical_terms)} medical terms")
        return medical_terms
    
    def _sanitize_result_for_caching(self, result: Dict[str, any]) -> Dict[str, any]:
        """
        Sanitize result dictionary to ensure only JSON-serializable data is cached
        
        Args:
            result: Original result dictionary
            
        Returns:
            Sanitized dictionary safe for JSON serialization
        """
        import json
        
        def _deep_sanitize(obj):
            """Recursively sanitize an object"""
            if obj is None or isinstance(obj, (str, int, float, bool)):
                return obj
            elif isinstance(obj, list):
                sanitized_list = []
                for item in obj:
                    try:
                        # Test if item is serializable
                        json.dumps(item)
                        sanitized_list.append(_deep_sanitize(item))
                    except (TypeError, ValueError):
                        # Skip non-serializable items
                        print(f"Skipping non-serializable list item: {type(item)}")
                        continue
                return sanitized_list
            elif isinstance(obj, dict):
                sanitized_dict = {}
                for key, value in obj.items():
                    try:
                        # Test if key-value pair is serializable
                        json.dumps({key: value})
                        sanitized_dict[key] = _deep_sanitize(value)
                    except (TypeError, ValueError):
                        # Skip non-serializable key-value pairs
                        print(f"Skipping non-serializable dict item: {key} = {type(value)}")
                        continue
                return sanitized_dict
            else:
                # For other types, try to serialize, if it fails, skip
                try:
                    json.dumps(obj)
                    return obj
                except (TypeError, ValueError):
                    print(f"Skipping non-serializable object of type: {type(obj)}")
                    return None
        
        sanitized = _deep_sanitize(result)
        
        # Final validation - try to serialize the entire result
        try:
            json.dumps(sanitized)
            return sanitized
        except (TypeError, ValueError) as e:
            print(f"Final sanitization failed: {e}")
            # Return a minimal safe result
            return {
                "term": result.get("term", ""),
                "is_correct": bool(result.get("is_correct", False)),
                "suggestions": [s for s in result.get("suggestions", []) if isinstance(s, str)],
                "confidence": float(result.get("confidence", 0.0)),
                "source": str(result.get("source", ""))
            }

    def check_spelling(self, term: str, llm_identified: bool = False) -> Dict[str, any]:
        """
        Check if a medical term is spelled correctly
        
        Args:
            term: The term to check
            llm_identified: If True, term was identified by LLM as medical (higher confidence it's correct)
            
        Returns:
            Dictionary with spell check results
        """
        # Ensure llm_identified is actually a boolean (safety check)
        if not isinstance(llm_identified, bool):
            print(f"⚠️  Warning: llm_identified is not boolean: {type(llm_identified)}, converting to bool")
            llm_identified = bool(llm_identified)
        
        result = {
            "term": term,
            "is_correct": bool(llm_identified),  # Ensure it's always boolean
            "suggestions": [],
            "confidence": 0.8 if llm_identified else 0.0,  # Higher confidence for LLM terms
            "source": "llm_identified" if llm_identified else None
        }
        
        # Check our dynamic medicine list (confirmed correct)
        if self.dynamic_list.is_medicine(term):
            result["is_correct"] = True
            result["confidence"] = 1.0
            result["source"] = "dynamic_list"
            return result
        
        # Check our local dictionary
        if self.medical_dict.is_medical_term(term):
            correct_spelling = self.medical_dict.get_correct_spelling(term)
            if correct_spelling.lower() == term.lower():
                result["is_correct"] = True
                result["confidence"] = 1.0
                result["source"] = "local_dictionary"
            else:
                # Found a close match in dictionary - this is a spelling error
                result["is_correct"] = False
                result["suggestions"] = [correct_spelling]
                result["confidence"] = 0.9
                result["source"] = "local_dictionary"
            return result
        
        # Check cached SNOMED results first
        cached_result = self.dynamic_list.get_cached_snomed_result(term)
        if cached_result:
            result.update(cached_result)
            return result
        
        # Check with SNOMED CT (with timeout and error handling) - only if not in LLM-only mode
        if self.use_snomed_api and not self.llm_only_mode:
            try:
                if self.snomed_api.validate_term(term):
                    result["is_correct"] = True
                    result["confidence"] = 0.95
                    result["source"] = "snomed_ct"
                    # Cache the sanitized result
                    sanitized_result = self._sanitize_result_for_caching(result)
                    self.dynamic_list.cache_snomed_result(term, sanitized_result)
                    return result
            except Exception as e:
                print(f"SNOMED API error for term '{term}': {e}")
                # Check if we should switch to LLM-only mode due to persistent failures
                if hasattr(self.snomed_api, 'circuit_breaker_state') and self.snomed_api.circuit_breaker_state == "open":
                    print("SNOMED API circuit breaker is open - temporarily switching to LLM-only mode")
                    self.llm_only_mode = True
                
                # If LLM identified this term and SNOMED fails, keep it as correct
                if llm_identified:
                    print(f"Keeping LLM-identified term '{term}' as correct despite SNOMED timeout")
                    result["is_correct"] = True
                    result["confidence"] = 0.8
                    result["source"] = "llm_identified_snomed_timeout"
                    return result
        elif self.llm_only_mode:
            print(f"LLM-only mode: Skipping SNOMED check for term '{term}'")
            # In LLM-only mode, trust LLM identification more
            if llm_identified:
                result["is_correct"] = True
                result["confidence"] = 0.85
                result["source"] = "llm_only_mode"
                return result
        
        # Get suggestions from local dictionary
        local_suggestions = self.medical_dict.get_suggestions(term)
        
        # Get suggestions from SNOMED (with error handling) - only if not in LLM-only mode
        snomed_suggestions = []
        if self.use_snomed_api and not self.llm_only_mode:
            try:
                snomed_suggestions = self.snomed_api.get_suggestions(term, max_suggestions=3)
            except Exception as e:
                print(f"SNOMED suggestions error for term '{term}': {e}")
        
        # Combine and rank suggestions
        all_suggestions = []
        
        # Add local suggestions with higher priority
        for sugg in local_suggestions[:3]:
            all_suggestions.append({
                "term": sugg,
                "score": fuzz.ratio(term.lower(), sugg.lower()),
                "source": "local"
            })
        
        # Add SNOMED suggestions (only if available)
        if not self.llm_only_mode:
            for sugg in snomed_suggestions[:3]:
                if not any(s["term"].lower() == sugg.lower() for s in all_suggestions):
                    all_suggestions.append({
                        "term": sugg,
                        "score": fuzz.ratio(term.lower(), sugg.lower()),
                        "source": "snomed"
                    })
        
        # Sort by score and filter out low-quality suggestions
        all_suggestions.sort(key=lambda x: x["score"], reverse=True)
        
        # Only include suggestions with reasonable similarity (score > 60)
        good_suggestions = [s["term"] for s in all_suggestions if s["score"] > 60]
        
        # Extract just the terms for the result
        result["suggestions"] = good_suggestions[:5]
        
        # Try general spell checking as fallback
        if not result["suggestions"]:
            try:
                blob = TextBlob(term)
                corrected = str(blob.correct())
                if corrected.lower() != term.lower():
                    result["suggestions"] = [corrected]
                    result["source"] = "textblob"
            except:
                pass
        
        # For LLM-identified terms, only mark as incorrect if we have very strong suggestions
        if llm_identified and result["suggestions"]:
            # Check if suggestions have very high similarity (indicating likely spelling error)
            best_score = max([fuzz.ratio(term.lower(), sugg.lower()) for sugg in result["suggestions"]] + [0])
            if best_score < 85:  # Not similar enough to override LLM confidence
                result["suggestions"] = []  # Remove weak suggestions
                result["is_correct"] = True  # Keep as correct
                result["confidence"] = 0.8
        
        # Set confidence based on whether we have suggestions and term source
        if result["is_correct"]:
            result["confidence"] = 0.8 if llm_identified else 0.7
        else:
            result["confidence"] = 0.7 if result["suggestions"] else 0.3
        
        # Cache the sanitized result
        sanitized_result = self._sanitize_result_for_caching(result)
        self.dynamic_list.cache_snomed_result(term, sanitized_result)
        
        return result
    
    def identify_medical_terms(self, text: str) -> List[Tuple[str, int, int, str]]:
        """
        Main method: Identify medical terms using LLM-first approach
        
        Args:
            text: The text to analyze
            
        Returns:
            List of tuples (term, start_pos, end_pos, category)
        """
        return self.identify_medical_terms_llm(text)
    
    def _batch_check_terms(self, terms_batch: List[Tuple[str, int, int, str]], llm_identified: bool = False) -> List[Dict]:
        """
        Check a batch of terms efficiently with optimized processing
        
        Args:
            terms_batch: List of (term, start, end, category) tuples
            llm_identified: Whether terms were identified by LLM
            
        Returns:
            List of spell check results
        """
        results = []
        unique_terms = set()
        
        # Group identical terms to avoid duplicate processing
        term_groups = {}
        for term, start, end, category in terms_batch:
            term_key = term.lower().strip()
            if term_key not in term_groups:
                term_groups[term_key] = {
                    'original_term': term,
                    'positions': [],
                    'category': category
                }
            term_groups[term_key]['positions'].append((start, end))
        
        # Process unique terms only once
        for term_key, group_data in term_groups.items():
            original_term = group_data['original_term']
            positions = group_data['positions']
            category = group_data['category']
            
            # Check spelling once per unique term
            spell_result = self.check_spelling(original_term, llm_identified=llm_identified)
            
            # Create results for each occurrence
            for start, end in positions:
                result_copy = spell_result.copy()
                result_copy["start_pos"] = start
                result_copy["end_pos"] = end
                result_copy["category"] = category
                results.append(result_copy)
            
            unique_terms.add(term_key)
        
        return results

    def check_text(self, text: str) -> Dict[str, any]:
        """
        Check spelling of all medical terms in a text with optimized batch processing
        
        Args:
            text: The text to check
            
        Returns:
            Dictionary with spell check results and unique term counts
        """
        medical_terms = self.identify_medical_terms(text)
        
        if not medical_terms:
            return {
                "results": [],
                "unique_terms": [],
                "unique_count": 0,
                "total_occurrences": 0
            }
        
        # Determine if terms came from LLM (higher confidence they're correct)
        llm_available = bool(self.use_llm and self.llm_client)
        
        # Process in smaller batches to optimize performance and avoid timeouts
        batch_size = 20  # Reduced from 50 to 20 for better performance
        all_results = []
        all_unique_terms = set()
        
        print(f"Processing {len(medical_terms)} medical terms in batches of {batch_size}")
        
        for i in range(0, len(medical_terms), batch_size):
            batch = medical_terms[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(medical_terms) + batch_size - 1)//batch_size}")
            
            try:
                # Process batch with optimized checking
                batch_results = self._batch_check_terms(batch, llm_identified=llm_available)
                all_results.extend(batch_results)
                
                # Track unique terms from this batch
                for term, _, _, _ in batch:
                    all_unique_terms.add(term.lower().strip())
                    
            except Exception as e:
                print(f"Error processing batch {i//batch_size + 1}: {e}")
                # Continue with next batch even if one fails
                continue
        
        return {
            "results": all_results,
            "unique_terms": sorted(list(all_unique_terms)),
            "unique_count": len(all_unique_terms),
            "total_occurrences": len(all_results)
        }
    
    def add_medicine_to_dynamic_list(self, term: str):
        """Add a medicine term to the dynamic list"""
        self.dynamic_list.add_medicine(term)
    
    def get_dynamic_list_stats(self) -> Dict:
        """Get statistics about the dynamic medicine list"""
        return self.dynamic_list.get_stats()
    
    def get_medical_nlp_status(self) -> Dict:
        """Get medical NLP status and configuration"""
        status = self.medical_nlp.get_status()
        # Add spell checker configuration info
        status.update({
            "spell_checker_config": {
                "use_snomed_api": self.use_snomed_api,
                "llm_only_mode": self.llm_only_mode,
                "use_llm": self.use_llm,
                "snomed_circuit_breaker": getattr(self.snomed_api, 'circuit_breaker_state', 'unknown') if hasattr(self.snomed_api, 'circuit_breaker_state') else 'unknown'
            }
        })
        return status
    
    def enable_llm_only_mode(self):
        """Enable LLM-only mode (disable SNOMED API)"""
        self.llm_only_mode = True
        print("Enabled LLM-only mode - SNOMED API disabled")
    
    def disable_llm_only_mode(self):
        """Disable LLM-only mode (re-enable SNOMED API)"""
        self.llm_only_mode = False
        print("Disabled LLM-only mode - SNOMED API re-enabled")
    
    def reset_snomed_circuit_breaker(self):
        """Reset the SNOMED API circuit breaker"""
        if hasattr(self.snomed_api, 'circuit_breaker_state'):
            self.snomed_api.circuit_breaker_state = "closed"
            self.snomed_api.circuit_breaker_failures = 0
            self.snomed_api.circuit_breaker_opened_at = None
            print("SNOMED API circuit breaker reset")
            # Re-enable SNOMED API if it was disabled
            if self.llm_only_mode:
                self.llm_only_mode = False
                print("Re-enabled SNOMED API after circuit breaker reset")
    
    def correct_text(self, text: str, interactive: bool = False) -> str:
        """
        Automatically correct medical terms in text
        
        Args:
            text: The text to correct
            interactive: If True, ask user to confirm corrections
            
        Returns:
            Corrected text
        """
        corrections = self.check_text(text)
        
        # Sort by position in reverse order to avoid position shifts
        corrections.sort(key=lambda x: x["start_pos"], reverse=True)
        
        corrected_text = text
        
        for correction in corrections:
            if not correction["is_correct"] and correction["suggestions"]:
                original = correction["term"]
                suggestion = correction["suggestions"][0]
                
                if interactive:
                    print(f"\nFound: '{original}'")
                    print(f"Suggestions: {', '.join(correction['suggestions'][:3])}")
                    choice = input(f"Replace with '{suggestion}'? (y/n/other): ").lower()
                    
                    if choice == 'n':
                        continue
                    elif choice not in ['y', 'yes']:
                        # User wants to enter custom correction
                        suggestion = input("Enter correction: ")
                
                # Replace in text
                start = correction["start_pos"]
                end = correction["end_pos"]
                corrected_text = corrected_text[:start] + suggestion + corrected_text[end:]
        
        return corrected_text
    
    def get_contextual_suggestions(self, term: str, context: str, position: int) -> List[str]:
        """
        Get suggestions based on the context around the term
        
        Args:
            term: The term to get suggestions for
            context: The full text context
            position: Position of the term in the context
            
        Returns:
            List of contextual suggestions
        """
        # Extract surrounding words for context
        before_text = context[:position].split()[-5:]  # 5 words before
        after_text = context[position + len(term):].split()[:5]  # 5 words after
        
        suggestions = self.check_spelling(term)["suggestions"]
        
        # If we have context clues, we could refine suggestions
        # For example, if "take" appears before, it's likely a medication
        if any(word in ["take", "taking", "prescribed", "medication"] for word in before_text):
            # Prioritize medication suggestions
            med_suggestions = []
            for sugg in suggestions:
                if self.medical_dict.is_medical_term(sugg):
                    # Check if it's in our medication list
                    if any(sugg.lower() in meds for meds in list(self.medical_dict.medical_terms.values())[:10]):
                        med_suggestions.append(sugg)
            
            if med_suggestions:
                return med_suggestions + [s for s in suggestions if s not in med_suggestions]
        
        return suggestions
