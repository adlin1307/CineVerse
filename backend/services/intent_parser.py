"""
Intent Parser Service for Scout.

Converts natural language user messages into validated ParsedIntent objects
using the Phase 1 schema. Supports both LLM-based parsing (Gemini) and
deterministic fallback.

This service ONLY handles intent parsing - it does NOT generate recommendations.
"""

import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pydantic import ValidationError

from config import settings
from models.intent import ParsedIntent, RequestType, MediaType, IntentConfidence
from models.state import ConversationState, TemporaryConstraints


# Genre mappings for intent parsing
GENRE_MAP = {
    # Movie genres
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
    # TV genres
    10759: "Action & Adventure", 10762: "Kids", 10763: "News",
    10764: "Reality", 10765: "Sci-Fi & Fantasy", 10766: "Soap",
    10767: "Talk", 10768: "War & Politics"
}

# Reverse mapping: name -> ID
GENRE_NAME_TO_ID = {name.lower(): gid for gid, name in GENRE_MAP.items()}


class IntentParser:
    """
    Intent parser that converts natural language to ParsedIntent objects.
    
    Supports two modes:
    1. LLM-based (Gemini) - preferred when available
    2. Deterministic fallback - rule-based parsing
    
    Both modes produce the same validated ParsedIntent schema.
    """
    
    def __init__(self):
        self._gemini_configured_override = None
        self._client = None
    
    @property
    def gemini_configured(self) -> bool:
        if self._gemini_configured_override is not None:
            return self._gemini_configured_override
        if self._client is not None:
            return True
        return bool(
            settings.gemini_api_key and 
            settings.gemini_api_key != "your_gemini_api_key_here"
        )
    
    @gemini_configured.setter
    def gemini_configured(self, val: bool):
        self._gemini_configured_override = val
    
    def _get_client(self):
        """Get or create Gemini client."""
        if self._client is not None:
            return self._client
            
        if not self.gemini_configured:
            return None
        
        if self._client is None:
            os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
            
            try:
                from google import genai
                from google.genai.types import HttpOptions
                
                http_options = HttpOptions(timeout=12)
                self._client = genai.Client(http_options=http_options)
            except Exception as e:
                print(f"[WARNING] Failed to create Gemini client: {e}")
                return None
        
        return self._client
    
    async def parse_intent(
        self,
        user_message: str,
        conversation_state: Optional[ConversationState] = None
    ) -> ParsedIntent:
        """
        Parse user message into validated ParsedIntent.
        
        Args:
            user_message: Current user message
            conversation_state: Optional conversation state for context
        
        Returns:
            Validated ParsedIntent object
        
        Raises:
            ValueError: If parsing fails completely
        """
        if not user_message or not user_message.strip():
            raise ValueError("Empty message cannot be parsed")
        
        user_message = user_message.strip()
        
        # Try LLM parsing first if available
        if self.gemini_configured:
            try:
                return await self._parse_with_llm(user_message, conversation_state)
            except Exception as e:
                print(f"[INFO] LLM parsing failed or unconfigured, using fallback: {e}")
        
        # Fall back to deterministic parsing
        return self._parse_deterministic(user_message, conversation_state)
    
    async def _parse_with_llm(
        self,
        user_message: str,
        conversation_state: Optional[ConversationState]
    ) -> ParsedIntent:
        """
        Parse intent using Gemini LLM.
        
        Returns structured JSON matching ParsedIntent schema.
        """
        client = self._get_client()
        if not client:
            raise ValueError("Gemini client not available")
        
        # Build prompt with schema and context
        prompt = self._build_llm_prompt(user_message, conversation_state)
        system_instruction = self._get_system_instruction()
        
        import asyncio
        
        def call_gemini():
            # Support both mock interactions.create (used in unit tests) and generate_content (live SDK)
            if hasattr(client, "interactions") and hasattr(client.interactions, "create"):
                return client.interactions.create(
                    model=settings.gemini_model,
                    input=prompt,
                    system_instruction=system_instruction,
                    generation_config={"thinking_level": "low"}
                )
            else:
                from google.genai import types
                return client.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json"
                    )
                )
        
        # Hard timeout for LLM call (12s)
        loop = asyncio.get_event_loop()
        try:
            interaction = await asyncio.wait_for(
                loop.run_in_executor(None, call_gemini),
                timeout=12.0
            )
        except asyncio.TimeoutError:
            raise ValueError("LLM request timed out")
        
        if hasattr(interaction, "output_text"):
            response_text = interaction.output_text.strip()
        elif hasattr(interaction, "text"):
            response_text = interaction.text.strip()
        else:
            response_text = str(interaction).strip()
            
        # Parse and validate response
        return self._parse_llm_response(response_text, user_message)
    
    def _build_llm_prompt(
        self,
        user_message: str,
        conversation_state: Optional[ConversationState]
    ) -> str:
        """Build prompt for LLM with context."""
        parts = []
        
        if conversation_state:
            if not conversation_state.temporary_constraints.is_empty():
                constraints = conversation_state.get_active_constraints_summary()
                parts.append(f"Current active constraints: {json.dumps(constraints)}")
            
            if conversation_state.previous_recommendations:
                titles = [
                    f"{idx+1}. {r.get('title', 'Unknown')} ({r.get('release_date', '')[:4] if r.get('release_date') else ''})"
                    for idx, r in enumerate(conversation_state.previous_recommendations[:5])
                ]
                parts.append(f"Recently recommended titles to the user: {', '.join(titles)}")
        
        parts.append(f"User message: {user_message}")
        parts.append("\nRespond with JSON matching the ParsedIntent schema.")
        
        return "\n".join(parts)
    
    def _get_system_instruction(self) -> str:
        """Get system instruction for LLM."""
        genre_json = json.dumps(GENRE_MAP)
        
        return f"""You are Scout, an intelligent, movie-obsessed discovery assistant for CineVerse.
Your personality is witty, warm, playful, cheeky, and deeply knowledgeable about cinema and television.

Parse the user's message into a structured JSON object matching this schema:

{{
  "request_type": "fresh_search|refinement|constraint_only|correction|title_question|clarification|chat",
  "confidence": "high|medium|low",
  "media_type": "movie|tv|both|null",
  "include_genres": [genre_ids],
  "exclude_genres": [genre_ids],
  "mood": "relaxed|excited|emotional|curious|null",
  "emotional_sub_intent": "tearjerker|feelgood|bittersweet|hopeful|dark|thought_provoking|general|null",
  "tone_modifiers": ["darker", "lighter", etc],
  "provider_id": null,
  "provider_name": null,
  "watch_region": "IN",
  "min_year": null,
  "max_year": null,
  "runtime_preference": "under_90|90_to_130|flexible|null",
  "language": null,
  "popularity": "low|medium|high|null",
  "referenced_title_index": null,
  "response_message": "your natural conversational response",
  "clarification_needed": null,
  "raw_user_message": "user message text",
  "parser_used": "llm"
}}

Request types:
- chat: Pure conversation, greetings, banter, chit-chat, reactions ("heyyy", "how are you?", "lol you're funny", "thanks!"). Zero recommendations.
- fresh_search: Fresh search request ("suggest sci-fi movies", "actually give me a comedy", "hey recommend a thriller").
- refinement: Modify existing search while preserving context ("make them darker", "brooo I wanna cry", "shorter ones", "less mainstream").
- constraint_only: Add or remove constraints without replacing intent ("not romance though", "no horror", "only TV shows").
- title_question: Ask about a recommendation already shown ("what about the second one?", "why did you recommend that?"). Set referenced_title_index (1-indexed).
- correction: Correct an earlier misunderstanding or override a specific field ("actually I want movies, not shows").
- clarification: Truly ambiguous request where key information is missing.

Available genres: {genre_json}

CRITICAL RULES:
1. GREETINGS & CASUAL TALK ("heyyy", "how are you?", "thanks!", "lol"):
   - If the user is just saying hi or chatting with no recommendation request, use request_type="chat".
   - Respond warmly and conversationally. Do NOT trigger a search.
   - If user says "hey, recommend a thriller", recognize the greeting AND classify as "fresh_search".
2. EMOTIONAL INTENTS:
   - "brooo I wanna cry", "heartbreaking", "tearjerker" -> mood="emotional", emotional_sub_intent="tearjerker", include_genres=[18]
   - "feel-good", "uplifting", "heartwarming" -> mood="emotional", emotional_sub_intent="feelgood"
   - "bittersweet", "melancholy" -> mood="emotional", emotional_sub_intent="bittersweet"
3. HARD EXCLUSIONS:
   - "not romance though", "no horror", "without action" -> add to exclude_genres.
4. REFINEMENTS VS FRESH SEARCH:
   - "Make them darker", "shorter ones", "not romance though" are refinements on existing context.
   - "Actually, give me a comedy" is a fresh search that clears previous constraints.
5. NEVER invent movies, ratings, availability, or IDs. TMDB will be queried deterministically.
6. MEDIA TYPES & CORRECTIONS:
   - "movies and shows" or "shows and movies" -> media_type="both"
   - "what about TV shows? I need them not movies", "TV shows, not movies", "only TV shows" -> request_type="correction", media_type="tv". Preserve previous genres. NEVER classify as title_question.
   - "movies, not TV", "only movies" -> request_type="correction", media_type="movie".

Respond ONLY with valid JSON. No markdown backticks outside, no extra text."""
    
    def _parse_llm_response(
        self,
        response_text: str,
        user_message: str
    ) -> ParsedIntent:
        """Parse and validate LLM JSON response."""
        # Clean response
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}")
        
        # Support legacy test/mock format
        if "message" in data and ("response_message" not in data or not data.get("response_message")):
            data["response_message"] = data["message"]
            
        if "intent" in data and "request_type" not in data:
            intent_val = data["intent"]
            if intent_val in ("chat", "greeting"):
                data["request_type"] = RequestType.CHAT.value
            elif intent_val == "clarify":
                data["request_type"] = RequestType.CLARIFICATION.value
            else:
                data["request_type"] = RequestType.FRESH_SEARCH.value
                
        if "preferences" in data and isinstance(data["preferences"], dict):
            prefs = data["preferences"]
            for k in [
                "include_genres", "exclude_genres", "mood", "runtime_preference",
                "min_year", "max_year", "popularity", "media_type",
                "provider_id", "provider_name", "watch_region", "emotional_sub_intent"
            ]:
                if k in prefs and (k not in data or data[k] is None):
                    data[k] = prefs[k]

        # Add required fields if missing
        if "response_message" not in data or not data["response_message"]:
            data["response_message"] = "Let me find something for you."
        
        # Normalize request_type aliases
        req_type = data.get("request_type", "fresh_search")
        if req_type == "new_search":
            data["request_type"] = RequestType.FRESH_SEARCH.value
        elif req_type == "constraint_update":
            data["request_type"] = RequestType.CONSTRAINT_ONLY.value
            
        data["raw_user_message"] = user_message
        data["parser_used"] = "llm"
        
        # Validate with Pydantic
        try:
            return ParsedIntent(**data)
        except ValidationError as e:
            raise ValueError(f"LLM response failed validation: {e}")
    
    def _parse_deterministic(
        self,
        user_message: str,
        conversation_state: Optional[ConversationState]
    ) -> ParsedIntent:
        """
        Deterministic fallback parser using rule-based matching.
        
        Follows the same schema and validation as the LLM path.
        """
        message_clean = user_message.strip()
        message_lower = message_clean.lower()
        
        # Get current context
        has_context = (
            conversation_state is not None and 
            not conversation_state.temporary_constraints.is_empty()
        )
        
        # 1. Check for pure greeting or chat messages
        chat_intent = self._check_pure_chat(message_lower, user_message)
        if chat_intent:
            return chat_intent
        
        # 2. Check for creator / director queries (e.g. 'who directed Oppenheimer')
        creator_intent = self._check_creator_query(message_lower, user_message)
        if creator_intent:
            return creator_intent
        
        # 3. Check for title questions / references to previous recommendations
        title_q_intent = self._check_title_question(message_lower, user_message, conversation_state)
        if title_q_intent:
            return title_q_intent
        
        # 4. Extract language and region
        language, lang_region = self._extract_language(message_lower)
        
        # 5. Detect media type
        media_type = self._extract_media_type(message_lower, conversation_state)
        if not media_type and any(k in message_lower for k in ['kdrama', 'k-drama', 'korean drama']):
            media_type = MediaType.TV
        
        # 6. Detect provider & region
        provider_id, provider_name, watch_region = self._extract_provider(message_lower)
        if lang_region and not provider_id:
            watch_region = lang_region
        
        # 7. Detect genre inclusions & exclusions
        include_genres, exclude_genres = self._extract_genres(message_lower, media_type)
        
        # 8. Detect emotional sub-intent & mood
        mood, emotional_sub_intent = self._extract_emotional_intent(message_lower, conversation_state)
        
        # 9. Detect similar title references (e.g. 'something like Interstellar')
        similar_title = self._extract_similar_title(message_lower)
        if similar_title:
            sim_genres, sim_mood = self._map_similar_title_to_genres(similar_title)
            for g in sim_genres:
                if g not in include_genres and g not in exclude_genres:
                    include_genres.append(g)
            if sim_mood and not mood:
                mood = sim_mood
        
        # If emotional sub-intent is present and Drama (18) is not in genres/exclusions:
        if mood == "emotional" or emotional_sub_intent:
            if 18 not in exclude_genres and 18 not in include_genres:
                include_genres.append(18)
            if emotional_sub_intent == "feelgood" and 10751 not in exclude_genres and 10751 not in include_genres:
                include_genres.append(10751)
        
        # 10. Detect tone modifiers (e.g., darker, lighter)
        tone_modifiers = self._extract_tone_modifiers(message_lower)
        if tone_modifiers:
            include_genres, tone_mood = self._apply_tone_genre_mapping(tone_modifiers, include_genres)
            if tone_mood and not mood:
                mood = tone_mood
        
        # 11. Detect runtime, popularity & release years
        runtime_pref = self._extract_runtime(message_lower)
        popularity = self._extract_popularity(message_lower)
        min_year, max_year = self._extract_year_range(message_lower)
        
        # 12. Detect request type
        request_type = self._detect_request_type(
            message_lower,
            has_context,
            include_genres=include_genres,
            exclude_genres=exclude_genres,
            provider_id=provider_id,
            tone_modifiers=tone_modifiers,
            emotional_sub_intent=emotional_sub_intent
        )
        
        # 13. Generate conversational response message
        response_msg = self._generate_response_message(
            request_type=request_type,
            media_type=media_type,
            include_genres=include_genres,
            exclude_genres=exclude_genres,
            mood=mood,
            emotional_sub_intent=emotional_sub_intent,
            tone_modifiers=tone_modifiers,
            provider_name=provider_name,
            raw_user_message=user_message
        )
        
        return ParsedIntent(
            request_type=request_type,
            confidence=IntentConfidence.HIGH if has_context else IntentConfidence.MEDIUM,
            media_type=media_type,
            include_genres=include_genres,
            exclude_genres=exclude_genres,
            mood=mood,
            emotional_sub_intent=emotional_sub_intent,
            tone_modifiers=tone_modifiers,
            provider_id=provider_id,
            provider_name=provider_name,
            watch_region=watch_region,
            min_year=min_year,
            max_year=max_year,
            runtime_preference=runtime_pref,
            language=language,
            popularity=popularity,
            referenced_title_name=similar_title,
            response_message=response_msg,
            raw_user_message=user_message,
            parser_used="fallback"
        )
    
    def _check_pure_chat(self, message_lower: str, raw_user_message: str) -> Optional[ParsedIntent]:
        """
        Check if message is a pure greeting, casual banter, or reaction with NO recommendation request.
        """
        # Check gratitude first so "thanks for the recommendations" is treated as CHAT
        gratitude_patterns = [
            r'^\s*(thanks+|thank you+|thx|cheers|appreciate it)\b'
        ]
        if any(re.search(p, message_lower) for p in gratitude_patterns):
            return ParsedIntent(
                request_type=RequestType.CHAT,
                confidence=IntentConfidence.HIGH,
                response_message="You're very welcome! Whenever you need another cinema tip, I'm right here.",
                raw_user_message=raw_user_message,
                parser_used="fallback"
            )

        # If there are explicit recommendation actions or genre names, it's NOT pure chat!
        rec_signals = [
            'recommend', 'suggestion', 'suggest', 'find me', 'show me', 'give me',
            'what should i watch', 'looking for', 'want to watch', 'in the mood for',
            'thriller', 'comedy', 'horror', 'action', 'drama', 'sci-fi', 'scifi',
            'romance', 'documentary', 'animation', 'fantasy', 'tearjerker',
            'disney', 'netflix', 'hotstar', 'hbo', 'prime video',
            'surprise me', 'surprise', 'movie night', 'something fun', 'pick something',
            'what to watch', 'pick a', 'something good', 'help me pick', 'underrated',
            'hidden gem', 'blockbuster'
        ]
        if any(sig in message_lower for sig in rec_signals):
            return None
        
        # Elongated greetings: "heyyy", "hiii", "hellooo", "yooo", "sup", "howdy", "good morning", etc.
        greeting_patterns = [
            r'^\s*h+[eai]+y+\b',
            r'^\s*h+i+\b',
            r'^\s*h+e+l+l+o+\b',
            r'^\s*y+o+\b',
            r'^\s*s+u+p+\b',
            r'^\s*h+o+w+d+y+\b',
            r'^\s*greetings\b',
            r'^\s*good\s+(morning|afternoon|evening|day|night)\b'
        ]
        is_greeting = any(re.search(p, message_lower) for p in greeting_patterns)
        
        # Casual conversational questions
        casual_patterns = [
            r'\bhow are you\b',
            r'\bhow(\'s|s) it going\b',
            r'\bwhat(\'s|s) up\b',
            r'\bwhats up\b',
            r'\bhow you doing\b',
            r'\bwhat are you doing\b',
            r'\bwho are you\b',
            r'\bwhat can you do\b',
            r'\bcan you help\b',
            r'\bhow does this work\b',
            r'\bwho made you\b',
            r'\btell me about yourself\b'
        ]
        is_casual = any(re.search(p, message_lower) for p in casual_patterns)
        
        # Banter / laughter / compliments
        banter_patterns = [
            r'\b(lol+|lmao+|haha+|rofl)\b',
            r'\byou(\'re|re) (funny|cool|great|awesome|hilarious)\b',
            r'\bfunny bot\b',
            r'\bnice one\b'
        ]
        is_banter = any(re.search(p, message_lower) for p in banter_patterns)
        
        # Gratitude
        gratitude_patterns = [
            r'\b(thanks+|thank you+|thx|cheers|appreciate it)\b'
        ]
        is_gratitude = any(re.search(p, message_lower) for p in gratitude_patterns)
        
        # Allow natural greetings/casual chat without strict 7-word cutoff
        words = message_lower.split()
        if len(words) <= 30:
            if is_casual:
                if any(w in message_lower for w in ["who are you", "what are you", "tell me about yourself", "what can you do"]):
                    response_text = "I'm Scout, CineVerse's cinema projectionist and discovery companion! Tell me what genres, moods, or titles you love, and I'll find your next great watch."
                else:
                    response_text = "Doing great, just hanging out in the projection room! What kind of movies or shows are you in the mood for?"
                return ParsedIntent(
                    request_type=RequestType.CHAT,
                    confidence=IntentConfidence.HIGH,
                    response_message=response_text,
                    raw_user_message=raw_user_message,
                    parser_used="fallback"
                )
            if is_greeting:
                return ParsedIntent(
                    request_type=RequestType.CHAT,
                    confidence=IntentConfidence.HIGH,
                    response_message="Hey! Ready to find your next favorite watch? Tell me what vibe or genre you're feeling tonight!",
                    raw_user_message=raw_user_message,
                    parser_used="fallback"
                )
            if is_banter:
                return ParsedIntent(
                    request_type=RequestType.CHAT,
                    confidence=IntentConfidence.HIGH,
                    response_message="Glad I could bring some entertainment! Ready to find something great to watch?",
                    raw_user_message=raw_user_message,
                    parser_used="fallback"
                )
            if is_gratitude:
                return ParsedIntent(
                    request_type=RequestType.CHAT,
                    confidence=IntentConfidence.HIGH,
                    response_message="You're very welcome! Whenever you need another cinema tip, I'm right here.",
                    raw_user_message=raw_user_message,
                    parser_used="fallback"
                )
        
        return None
    
    def _check_title_question(
        self,
        message_lower: str,
        raw_user_message: str,
        conversation_state: Optional[ConversationState]
    ) -> Optional[ParsedIntent]:
        """
        Check if message is asking about a title from previous recommendations.
        e.g., 'what about the second one?', 'why did you recommend that?'
        """
        title_q_patterns = [
            r'\b(what about|tell me about|tell me more about|who is in|why did you recommend|why that one|why this one|how about)\b'
        ]
        if not any(re.search(p, message_lower) for p in title_q_patterns):
            return None

        # If user is talking about media types or format switches, this is NOT a title question
        media_correction_terms = [
            'tv show', 'tv shows', 'television', 'tv series', 'movies', 'films',
            'not movies', 'no movies', 'not tv', 'no tv', 'only tv', 'only movies',
            'tv only', 'movies only', 'instead of movies', 'instead of tv'
        ]
        if any(term in message_lower for term in media_correction_terms):
            return None
        
        # Extract ordinal index if referenced
        index = None
        if re.search(r'\b(first|1st|number 1|#1)\b', message_lower):
            index = 1
        elif re.search(r'\b(second|2nd|number 2|#2)\b', message_lower):
            index = 2
        elif re.search(r'\b(third|3rd|number 3|#3)\b', message_lower):
            index = 3
        elif re.search(r'\b(fourth|4th|number 4|#4)\b', message_lower):
            index = 4
        elif re.search(r'\b(last|final)\b', message_lower):
            index = -1
        
        # If no ordinal index is specified, verify it explicitly refers to a previous recommendation
        specific_title_refs = [
            'that one', 'this one', 'the first', 'the second', 'the third',
            'why did you', 'who is in', 'who stars in', 'tell me about that',
            'tell me about this', 'tell me about the'
        ]
        if index is None and not any(p in message_lower for p in specific_title_refs):
            return None
        
        # Build answer if we have previous recommendations
        response_msg = "Here are the details on that pick."
        if conversation_state and conversation_state.previous_recommendations:
            rec_list = conversation_state.previous_recommendations
            target_item = None
            if index is not None and 1 <= index <= len(rec_list):
                target_item = rec_list[index - 1]
            elif index == -1 and rec_list:
                target_item = rec_list[-1]
            elif rec_list:
                target_item = rec_list[0]
            
            if target_item:
                title = target_item.get("title", "That title")
                year = target_item.get("release_date", "")[:4]
                year_str = f" ({year})" if year else ""
                rating = target_item.get("vote_average")
                rating_str = f"rated {rating:.1f}/10 on TMDB" if rating else "well-reviewed"
                overview = target_item.get("overview") or target_item.get("explanation") or ""
                response_msg = f"{title}{year_str} is {rating_str}. {overview}".strip()
        
        return ParsedIntent(
            request_type=RequestType.TITLE_QUESTION,
            confidence=IntentConfidence.HIGH,
            referenced_title_index=index,
            response_message=response_msg,
            raw_user_message=raw_user_message,
            parser_used="fallback"
        )
    
    def _detect_request_type(
        self,
        message_lower: str,
        has_context: bool,
        include_genres: List[int],
        exclude_genres: List[int],
        provider_id: Optional[int],
        tone_modifiers: List[str],
        emotional_sub_intent: Optional[str]
    ) -> RequestType:
        """Detect request type from message semantics."""
        # 1. Fresh search indicators
        fresh_indicators = [
            r'\bnow suggest\b', r'\binstead suggest\b', r'\bsuggest some\b',
            r'\brecommend some\b', r'\bfind me\b', r'\bshow me\b',
            r'\bstart fresh\b', r'\bsomething completely different\b',
            r'\bstart over\b', r'\bnew search\b', r'\bactually give me\b',
            r'\bactually, give me\b', r'\bnow give me\b'
        ]
        if any(re.search(p, message_lower) for p in fresh_indicators):
            return RequestType.FRESH_SEARCH
        
        # 2. Correction indicators
        correction_words = [
            r'\bactually\b', r'\bmeant\b', r'\bchange to\b', r'\bswitch to\b',
            r'\bnot movies\b', r'\bno movies\b', r'\bnot tv\b', r'\bno tv\b',
            r'\bneed them not\b', r'\bwhat about tv\b', r'\bwhat about shows\b',
            r'\bhow about tv\b', r'\bonly tv\b', r'\bonly movies\b'
        ]
        if any(re.search(w, message_lower) for w in correction_words):
            # If changing genre or media type, it's correction or fresh search
            return RequestType.CORRECTION
        
        # 3. Pure constraint indicators: "not romance though", "no horror please", "without action"
        # If user ONLY specifies exclusions or filters without asking for a fresh new genre
        if exclude_genres and not include_genres and not provider_id:
            return RequestType.CONSTRAINT_ONLY
        
        # Constraint-only phrases
        constraint_patterns = [
            r'^(not\s+\w+|no\s+\w+|without\s+\w+|skip\s+\w+)(\s+though|\s+please)?$'
        ]
        if any(re.search(p, message_lower.strip()) for p in constraint_patterns):
            return RequestType.CONSTRAINT_ONLY
        
        # 4. Refinement indicators (requires context)
        refinement_patterns = [
            r'\bmore\b', r'\bless\b', r'\bdarker\b', r'\blighter\b',
            r'\bshorter\b', r'\blonger\b', r'\bmake (it|them)\b',
            r'\bunderrated\b', r'\bless mainstream\b', r'\bwanna cry\b',
            r'\bwant to cry\b'
        ]
        is_refinement = has_context and any(re.search(p, message_lower) for p in refinement_patterns)
        if is_refinement:
            return RequestType.REFINEMENT
        
        # If context exists and user is just narrowing emotional sub-intent (e.g. "brooo I wanna cry")
        if has_context and emotional_sub_intent == "tearjerker":
            return RequestType.REFINEMENT
            
        # If context exists and user adds tone
        if has_context and tone_modifiers:
            return RequestType.REFINEMENT
        
        # If no context, no genres, no exclusions, no provider, no tone, and no emotional intent:
        # Verify if the user is actually expressing a discovery/search request
        if not has_context and not include_genres and not exclude_genres and not provider_id and not tone_modifiers and not emotional_sub_intent:
            discovery_signals = [
                'surprise', 'fun for tonight', 'something fun', 'movie night', 'movie', 'movies',
                'film', 'films', 'show', 'shows', 'series', 'watch', 'recommend', 'suggestion',
                'suggest', 'find', 'pick', 'give me', 'looking for', 'underrated', 'gem',
                'something to watch', 'what to watch', 'something good', 'cinema', 'stream'
            ]
            if not any(sig in message_lower for sig in discovery_signals):
                return RequestType.CHAT
        
        return RequestType.FRESH_SEARCH
    
    def _extract_media_type(
        self,
        message_lower: str,
        conversation_state: Optional[ConversationState]
    ) -> Optional[MediaType]:
        """Extract media type from message with negation and correction support."""
        # Detect explicit negations of movies or TV
        negate_movie = bool(
            re.search(r'\b(not|no|without|instead of)\s+(movies?|films?|cinema)\b', message_lower) or
            re.search(r'\b(movies?|films?|cinema)\s+not\b', message_lower) or
            re.search(r'\bneed\s+(them\s+)?not\s+(movies?|films?)\b', message_lower)
        )
        negate_tv = bool(
            re.search(r'\b(not|no|without|instead of)\s+(tv|shows?|series|television)\b', message_lower) or
            re.search(r'\b(tv|shows?|series)\s+not\b', message_lower) or
            re.search(r'\bneed\s+(them\s+)?not\s+(tv|shows?|series)\b', message_lower)
        )
        
        explicit_only_tv = bool(
            re.search(r'\b(only|just)\s+(tv|shows?|series)\b', message_lower) or
            re.search(r'\b(tv|shows?|series)\s+only\b', message_lower) or
            re.search(r'\btv\s+shows?,?\s+not\s+movies?\b', message_lower)
        )
        explicit_only_movie = bool(
            re.search(r'\b(only|just)\s+(movies?|films?)\b', message_lower) or
            re.search(r'\b(movies?|films?)\s+only\b', message_lower) or
            re.search(r'\bmovies?,?\s+not\s+(tv|shows?|series)\b', message_lower)
        )
        
        if explicit_only_tv or (negate_movie and not negate_tv):
            return MediaType.TV
        if explicit_only_movie or (negate_tv and not negate_movie):
            return MediaType.MOVIE

        has_tv = any(w in message_lower for w in ['tv show', 'tv series', 'series', 'tv', 'episodes', 'shows']) and not negate_tv
        has_movie = any(w in message_lower for w in ['movie', 'movies', 'film', 'films', 'cinema']) and not negate_movie
        
        if has_tv and not has_movie:
            return MediaType.TV
        elif has_movie and not has_tv:
            return MediaType.MOVIE
        elif has_tv and has_movie:
            return MediaType.BOTH
        elif 'both' in message_lower or 'either' in message_lower:
            return MediaType.BOTH
        elif conversation_state and conversation_state.temporary_constraints.media_type:
            # If this is a fresh search statement with no media type mentioned, reset media type
            fresh_indicators = [
                r'\bnow suggest\b', r'\binstead suggest\b', r'\bsuggest some\b',
                r'\brecommend some\b', r'\bfind me\b', r'\bshow me\b',
                r'\bstart fresh\b', r'\bsomething completely different\b',
                r'\bstart over\b', r'\bnew search\b', r'\bactually give me\b',
                r'\bactually, give me\b', r'\bnow give me\b'
            ]
            if any(re.search(p, message_lower) for p in fresh_indicators):
                return None
            return conversation_state.temporary_constraints.media_type
        
        return None
    
    def _extract_provider(self, message_lower: str) -> Tuple[Optional[int], Optional[str], str]:
        """Extract streaming provider and region."""
        watch_region = settings.watch_region or "IN"
        
        # Disney+ / Hotstar
        if any(word in message_lower for word in ['disney', 'disney+', 'disney plus', 'hotstar']):
            if watch_region == "US":
                return 337, "Disney+", "US"
            elif watch_region == "IN":
                return 2336, "Disney+ Hotstar", "IN"
            else:
                return 337, "Disney+", watch_region
        
        # Netflix
        if 'netflix' in message_lower:
            return 8, "Netflix", watch_region
        
        # Prime Video
        if any(word in message_lower for word in ['prime', 'amazon prime', 'prime video']):
            if watch_region == "IN":
                return 119, "Prime Video", "IN"
            else:
                return 9, "Prime Video", "US"
        
        # HBO Max / Max
        if any(word in message_lower for word in ['hbo', 'max', 'hbo max']):
            if watch_region == "US":
                return 1899, "Max", "US"
            else:
                return None, "Max", watch_region
        
        return None, None, watch_region
    
    def _extract_genres(
        self,
        message_lower: str,
        media_type: Optional[MediaType]
    ) -> Tuple[List[int], List[int]]:
        """Extract include and exclude genre IDs with slang & repeated-character normalization."""
        include_genres = []
        exclude_genres = []
        
        # Normalize repeated characters (e.g. 'horrorrr' -> 'horror', 'scifiii' -> 'scifi')
        norm_message = re.sub(r'([a-zA-Z])\1{2,}', r'\1', message_lower)
        
        genre_keywords = {
            'science fiction': (878, 10765),
            'action & adventure': (28, 10759),
            'action and adventure': (28, 10759),
            'romantic comedy': (10749, 35),
            'rom-com': (10749, 35),
            'sci-fi': (878, 10765),
            'scifi': (878, 10765),
            'action': (28, 10759),
            'comedy': (35, 35),
            'drama': (18, 18),
            'horror': (27, 27),
            'thriller': (53, 53),
            'romance': (10749, 10749),
            'romantic': (10749, 10749),
            'animation': (16, 16),
            'animated': (16, 16),
            'cartoon': (16, 16),
            'cartoons': (16, 16),
            'anime': (16, 16),
            'family': (10751, 10751),
            'documentary': (99, 99),
            'fantasy': (14, 10765),
            'mystery': (9648, 9648),
            'crime': (80, 80),
            'western': (37, 37),
            'war': (10752, 10768),
            'musical': (10402, 10402),
            'music': (10402, 10402),
            'jump scares': (27, 27),
            'jump scare': (27, 27),
            'gore': (27, 27),
        }
        
        negative_patterns = [
            r'\bno\s+(?:any\s+)?',
            r'\bnothing\s+with\s+',
            r'\bwithout\s+(?:any\s+)?',
            r'\bexclude\s+(?:any\s+)?',
            r'\bskip\s+(?:any\s+)?',
            r'\bnot\s+(?:any\s+)?',
            r'\bhate\s+',
            r'\bavoid\s+(?:any\s+)?',
            r'\bleave\s+out\s+(?:any\s+)?',
            r'\bno\s+more\s+',
            r'\bdon\'?t\s+want\s+(?:any\s+)?',
            r'\bdo\s+not\s+want\s+(?:any\s+)?',
            r'\bzero\s+',
            r'\bnever\s+',
            r'\bno\b(?:\s+\w+){0,3}\s+with\s+'
        ]
        
        matched_positions = set()
        
        for keyword, (movie_id, tv_id) in genre_keywords.items():
            found_in_raw = keyword in message_lower
            found_in_norm = keyword in norm_message
            if not found_in_raw and not found_in_norm:
                continue
            
            target_msg = norm_message if found_in_norm else message_lower
            keyword_start = target_msg.find(keyword)
            if keyword_start == -1:
                continue
            
            keyword_end = keyword_start + len(keyword)
            keyword_range = set(range(keyword_start, keyword_end))
            if keyword_range & matched_positions:
                continue
            
            matched_positions.update(keyword_range)
            
            keyword_escaped = re.escape(keyword)
            is_negative = any(
                re.search(f"{pattern}{keyword_escaped}", target_msg)
                for pattern in negative_patterns
            ) or any(
                re.search(f"{pattern}{keyword_escaped}", message_lower)
                for pattern in negative_patterns
            )
            
            if media_type == MediaType.TV:
                genre_id = tv_id
            elif media_type == MediaType.MOVIE:
                genre_id = movie_id
            else:
                genre_id = movie_id
                if tv_id != movie_id:
                    if is_negative:
                        if tv_id not in exclude_genres:
                            exclude_genres.append(tv_id)
                        if tv_id in include_genres:
                            include_genres.remove(tv_id)
                    else:
                        if tv_id not in exclude_genres and tv_id not in include_genres:
                            include_genres.append(tv_id)
            
            if is_negative:
                if genre_id not in exclude_genres:
                    exclude_genres.append(genre_id)
                if genre_id in include_genres:
                    include_genres.remove(genre_id)
            else:
                if genre_id not in exclude_genres and genre_id not in include_genres:
                    include_genres.append(genre_id)
        
        return include_genres, exclude_genres
    
    def _extract_emotional_intent(
        self,
        message_lower: str,
        conversation_state: Optional[ConversationState]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract mood and nuanced emotional sub-intent with slang normalization."""
        mood = None
        sub_intent = None
        
        # Normalize repeated characters (e.g. 'cryyy' -> 'cry', 'sadnesss' -> 'sadness')
        norm_message = re.sub(r'([a-zA-Z])\1{2,}', r'\1', message_lower)
        combined_text = f"{message_lower} {norm_message}"
        
        tearjerker_words = [
            'cry', 'crying', 'sob', 'sobbing', 'tear', 'tears', 'heartbreaking', 'heartbreak',
            'devastating', 'gut-wrenching', 'sad ending', 'wanna cry', 'want to cry', 'bawl',
            'grief', 'tragic', 'tragedy', 'mourning'
        ]
        bittersweet_words = [
            'bittersweet', 'melancholy', 'wistful', 'nostalgic', 'parting', 'wistfulness'
        ]
        hopeful_words = [
            'hopeful', 'cathartic', 'catharsis', 'resilience', 'redemption', 'survival',
            'healing', 'second chance', 'overcoming', 'triumph of the human spirit'
        ]
        feelgood_words = [
            'feel-good', 'feel good', 'feelgood', 'heartwarming', 'uplifting',
            'comforting', 'inspiring', 'wholesome', 'charming', 'cheerful', 'cozy'
        ]
        intense_words = [
            'emotionally intense', 'intense drama', 'emotional intensity', 'gut punch',
            'gut-punch', 'gripping drama', 'heavy drama', 'pressure cooker'
        ]
        thought_provoking_words = [
            'thought-provoking', 'thought provoking', 'mind-bending', 'philosophical',
            'existential', 'deep meaning', 'profound'
        ]
        general_emotional_words = [
            'emotional', 'moving', 'touching', 'dramatic', 'heavy'
        ]
        
        if any(w in combined_text for w in intense_words):
            mood = "emotional"
            sub_intent = "intense"
        elif any(w in combined_text for w in tearjerker_words):
            mood = "emotional"
            sub_intent = "tearjerker"
        elif any(w in combined_text for w in bittersweet_words):
            mood = "emotional"
            sub_intent = "bittersweet"
        elif any(w in combined_text for w in hopeful_words):
            mood = "emotional"
            sub_intent = "hopeful"
        elif any(w in combined_text for w in feelgood_words):
            mood = "emotional"
            sub_intent = "feelgood"
        elif any(w in combined_text for w in thought_provoking_words):
            mood = "curious"
            sub_intent = "thought_provoking"
        elif any(w in combined_text for w in general_emotional_words):
            mood = "emotional"
            sub_intent = "general"
        elif any(w in combined_text for w in ['relaxed', 'chill', 'easy', 'light', 'fun', 'funny']):
            mood = "relaxed"
        elif any(w in combined_text for w in ['exciting', 'thrilling', 'adrenaline', 'action-packed']):
            mood = "excited"
        elif any(w in combined_text for w in ['curious', 'interesting', 'mysterious']):
            mood = "curious"
            
        # Inherit mood/sub-intent from previous conversation state ONLY if in refinement and not a fresh search / new genre
        is_fresh_indicator = any(
            w in message_lower for w in [
                'actually', 'instead', 'switch to', 'how about a', 'how about some',
                'start over', 'new search', 'give me a comedy', 'suggest a comedy'
            ]
        )
        if not is_fresh_indicator:
            if not sub_intent and conversation_state and conversation_state.temporary_constraints.emotional_sub_intent:
                sub_intent = conversation_state.temporary_constraints.emotional_sub_intent
            if not mood and conversation_state and conversation_state.temporary_constraints.mood:
                mood = conversation_state.temporary_constraints.mood
            
        return mood, sub_intent
    
    def _extract_tone_modifiers(self, message_lower: str) -> List[str]:
        """Extract tone modifiers."""
        modifiers = []
        if 'darker' in message_lower or 'dark' in message_lower or 'gritty' in message_lower:
            modifiers.append('darker')
        if 'lighter' in message_lower or 'light' in message_lower or 'fun' in message_lower:
            modifiers.append('lighter')
        if 'intense' in message_lower:
            modifiers.append('intense')
        return modifiers
    
    def _extract_runtime(self, message_lower: str) -> Optional[str]:
        """Extract runtime preference with natural time phrase normalization."""
        under_90_patterns = [
            'short', 'shorter', 'quick', 'brief', 'bite-sized', 'under 90', 'less than 90',
            'under 90 minutes', 'under 90 mins', 'less than 90m', 'under an hour and a half',
            'under 1.5 hours', 'under 1.5h'
        ]
        standard_patterns = [
            'standard', '90 to 120', '90 to 130', 'medium length', 'under two hours',
            'under 2 hours', 'less than two hours', 'less than 2 hours', 'around 2 hours',
            'under 120 minutes', 'under 120 mins', 'under 2h', 'less than 2h'
        ]
        flexible_patterns = [
            'long', 'longer', 'epic', 'over 2 hours', 'over two hours', 'over 2.5 hours',
            'over 150 minutes'
        ]
        if any(p in message_lower for p in under_90_patterns):
            return 'under_90'
        if any(p in message_lower for p in standard_patterns):
            return '90_to_130'
        if any(p in message_lower for p in flexible_patterns):
            return 'flexible'
        return None

    def _extract_language(self, message_lower: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract language and associated watch region.
        Supports regional Indian cinema (Tamil, Telugu, Malayalam, Hindi) and international languages.
        """
        lang_map = {
            'tamil': ('ta', 'IN'),
            'kollywood': ('ta', 'IN'),
            'telugu': ('te', 'IN'),
            'tollywood': ('te', 'IN'),
            'malayalam': ('ml', 'IN'),
            'mollywood': ('ml', 'IN'),
            'hindi': ('hi', 'IN'),
            'bollywood': ('hi', 'IN'),
            'korean': ('ko', 'KR'),
            'kdrama': ('ko', 'KR'),
            'k-drama': ('ko', 'KR'),
            'japanese': ('ja', 'JP'),
            'anime': ('ja', 'JP'),
            'french': ('fr', 'FR'),
            'spanish': ('es', 'ES'),
            'german': ('de', 'DE'),
            'italian': ('it', 'IT'),
        }
        for word, (code, region) in lang_map.items():
            if re.search(rf'\b{word}\b', message_lower):
                return code, region
        return None, None

    def _extract_year_range(self, message_lower: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract release year constraints (min_year, max_year).
        Supports:
        - "after 2020", "post 2020", "since 2020"
        - "before 2000", "pre 2000", "prior to 2010"
        - "between 2010 and 2020", "from 2010 to 2020"
        - "90s", "80s", "70s", "2000s", "2010s", "2020s"
        - "released in 1910", "from 1910", "made in 1994"
        """
        # 1. Between range: "between 2010 and 2020", "from 2010 to 2020"
        between_match = re.search(
            r'\b(?:between|from)\s+(19\d\d|20[0-9]\d)\s+(?:and|to)\s+(19\d\d|20[0-9]\d)\b',
            message_lower
        )
        if between_match:
            y1, y2 = int(between_match.group(1)), int(between_match.group(2))
            return (min(y1, y2), max(y1, y2))
        
        # 2. Decades
        decade_map = {
            r'\b(?:the\s+)?(?:\'|19)?70s\b': (1970, 1979),
            r'\b(?:the\s+)?(?:\'|19)?80s\b': (1980, 1989),
            r'\b(?:the\s+)?(?:\'|19)?90s\b': (1990, 1999),
            r'\b(?:the\s+)?(?:20)?00s\b': (2000, 2009),
            r'\b(?:the\s+)?(?:20)?10s\b': (2010, 2019),
            r'\b(?:the\s+)?(?:20)?20s\b': (2020, 2029),
        }
        for pat, (d_min, d_max) in decade_map.items():
            if re.search(pat, message_lower):
                return (d_min, d_max)

        # 3. After / Post / Since
        after_match = re.search(
            r'\b(?:released\s+)?(?:after|post|since|newer\s+than)\s+(19\d\d|20[0-9]\d)\b',
            message_lower
        )
        if after_match:
            year = int(after_match.group(1))
            if "since" in message_lower:
                return (year, None)
            return (year + 1, None)
        
        # 4. Before / Pre / Prior to
        before_match = re.search(
            r'\b(?:released\s+)?(?:before|pre|prior\s+to|older\s+than)\s+(19\d\d|20[0-9]\d)\b',
            message_lower
        )
        if before_match:
            year = int(before_match.group(1))
            return (None, year - 1)

        # 5. Exact year: "released in 1910", "made in 1994", "from 1910", "in the year 2021"
        exact_match = re.search(
            r'\b(?:released\s+in|made\s+in|from\s+the\s+year|from\s+year|in\s+the\s+year|from)\s+(19\d\d|20[0-9]\d)\b',
            message_lower
        )
        if exact_match:
            year = int(exact_match.group(1))
            return (year, year)

        # 6. "in <year>"
        in_match = re.search(
            r'\b(?:released\s+)?in\s+(19\d\d|20[0-9]\d)\b',
            message_lower
        )
        if in_match:
            year = int(in_match.group(1))
            return (year, year)

        # 7. Standalone year before a media word: "1910 movie", "2023 film", "2022 thriller"
        standalone_match = re.search(
            r'\b(19\d\d|20[0-9]\d)\s+(?:movie|movies|film|films|cinema|thriller|comedy|drama|action|horror|show|series)\b',
            message_lower
        )
        if standalone_match:
            year = int(standalone_match.group(1))
            return (year, year)

        return (None, None)

    def _check_creator_query(self, message_lower: str, raw_user_message: str) -> Optional[ParsedIntent]:
        """Check for director/creator/actor specific questions."""
        who_directed_match = re.search(
            r'\b(?:who\s+directed|who\s+is\s+the\s+director\s+of|who\s+made|director\s+of)\s+([A-Za-z0-9\s\':\-\.]+)',
            message_lower
        )
        if who_directed_match:
            title = who_directed_match.group(1).strip()
            directors = {
                'oppenheimer': 'Christopher Nolan',
                'interstellar': 'Christopher Nolan',
                'inception': 'Christopher Nolan',
                'tenet': 'Christopher Nolan',
                'dunkirk': 'Christopher Nolan',
                'the dark knight': 'Christopher Nolan',
                'memento': 'Christopher Nolan',
                'the prestige': 'Christopher Nolan',
                'dune': 'Denis Villeneuve',
                'blade runner 2049': 'Denis Villeneuve',
                'arrival': 'Denis Villeneuve',
                'sicario': 'Denis Villeneuve',
                'parasite': 'Bong Joon-ho',
                'snowpiercer': 'Bong Joon-ho',
                'pulp fiction': 'Quentin Tarantino',
                'inglourious basterds': 'Quentin Tarantino',
                'django unchained': 'Quentin Tarantino',
                'kill bill': 'Quentin Tarantino',
                'titanic': 'James Cameron',
                'avatar': 'James Cameron',
                'jurassic park': 'Steven Spielberg',
                'schindler\'s list': 'Steven Spielberg',
                'jaws': 'Steven Spielberg',
                'goodfellas': 'Martin Scorsese',
                'taxi driver': 'Martin Scorsese',
                'the wolf of wall street': 'Martin Scorsese',
                'fight club': 'David Fincher',
                'se7en': 'David Fincher',
                'the social network': 'David Fincher',
                'vikram': 'Lokesh Kanagaraj',
                'kaithi': 'Lokesh Kanagaraj',
                'leo': 'Lokesh Kanagaraj',
                'jailer': 'Nelson Dilipkumar',
                'baahubali': 'S. S. Rajamouli',
                'rrr': 'S. S. Rajamouli',
            }
            clean_title = re.sub(r'[^\w\s]', '', title).strip()
            ans_director = None
            for k, d in directors.items():
                if k in title or k in clean_title:
                    ans_director = (d, k.title())
                    break
            if ans_director:
                return ParsedIntent(
                    request_type=RequestType.TITLE_QUESTION,
                    confidence=IntentConfidence.HIGH,
                    referenced_title_name=ans_director[1],
                    response_message=f"{ans_director[0]} directed {ans_director[1]}.",
                    raw_user_message=raw_user_message,
                    parser_used="fallback"
                )
        return None

    def _extract_similar_title(self, message_lower: str) -> Optional[str]:
        """Extract title from 'like <title>' or 'similar to <title>'."""
        patterns = [
            r'\b(?:something\s+like|movies?\s+like|films?\s+like|shows?\s+like|series\s+like|similar\s+to|more\s+like|along\s+the\s+lines\s+of)\s+([A-Za-z0-9\s\':\-\.]+?)(?:\s+(?:please|tonight|recommend|movies?|films?|shows?|series)|$)',
            r'\b(?:fans\s+of|if\s+i\s+liked|if\s+i\s+loved)\s+([A-Za-z0-9\s\':\-\.]+?)(?:\s+(?:what|recommend|suggest)|$)'
        ]
        for pat in patterns:
            m = re.search(pat, message_lower)
            if m:
                title = m.group(1).strip()
                if title and title not in ['that', 'this', 'it', 'them', 'those', 'the first', 'the second', 'horror', 'action', 'comedy']:
                    return title
        return None

    def _map_similar_title_to_genres(self, title: str) -> Tuple[List[int], Optional[str]]:
        """Map common reference titles to verified genres and mood."""
        t = title.lower().strip()
        catalog = {
            'interstellar': ([878, 18], 'curious'),
            'inception': ([878, 28, 53], 'curious'),
            'the dark knight': ([28, 80, 18], 'excited'),
            'parasite': ([53, 18, 35], 'curious'),
            'the notebook': ([10749, 18], 'emotional'),
            'whiplash': ([18, 10402], 'excited'),
            'superbad': ([35], 'relaxed'),
            'the conjuring': ([27, 9648], 'excited'),
            'hereditary': ([27, 9648], 'excited'),
            'dune': ([878, 12], 'curious'),
            'blade runner': ([878, 9648], 'curious'),
            'knives out': ([9648, 35], 'curious'),
            'oppenheimer': ([18, 36], 'emotional'),
            'alien': ([27, 878], 'excited'),
            'pulp fiction': ([80, 18], 'excited'),
            'the matrix': ([878, 28], 'excited'),
            'get out': ([9648, 53, 27], 'curious'),
            'la la land': ([35, 18, 10402], 'emotional'),
            'spider-man': ([28, 12, 878], 'excited'),
            'avengers': ([28, 12, 878], 'excited'),
            'fight club': ([18, 53], 'curious'),
            'se7en': ([80, 9648, 53], 'curious'),
            'shutter island': ([18, 9648, 53], 'curious'),
            'silence of the lambs': ([80, 18, 53], 'curious'),
            'zodiac': ([80, 18, 9648], 'curious'),
            'goodfellas': ([18, 80], 'excited'),
            'godfather': ([18, 80], 'emotional'),
            'breaking bad': ([18, 80], 'excited'),
            'stranger things': ([10765, 18, 9648], 'curious'),
            'game of thrones': ([10765, 18, 10759], 'excited'),
            'vikram': ([28, 53], 'excited'),
            'leo': ([28, 53], 'excited'),
            'jailer': ([28, 35], 'excited'),
            'kaithi': ([28, 53], 'excited'),
            'master': ([28, 53], 'excited'),
            'asuran': ([28, 18], 'emotional'),
            'rrr': ([28, 18], 'excited'),
            'baahubali': ([28, 12, 14], 'excited'),
            'drishyam': ([80, 53, 18], 'curious')
        }
        for key, (genres, mood) in catalog.items():
            if key in t or t in key:
                return genres, mood
        return [], None
    
    def _extract_popularity(self, message_lower: str) -> Optional[str]:
        """Extract popularity preference."""
        if any(w in message_lower for w in ['underrated', 'hidden gem', 'less mainstream', 'less popular', 'obscure', 'indie']):
            return 'low'
        elif any(w in message_lower for w in ['popular', 'blockbuster', 'famous', 'well-known', 'hits']):
            return 'high'
        return None
    
    def _apply_tone_genre_mapping(
        self,
        tone_modifiers: List[str],
        include_genres: List[int]
    ) -> Tuple[List[int], Optional[str]]:
        """Apply genre additions based on tone modifiers."""
        mood = None
        if 'darker' in tone_modifiers:
            if 18 not in include_genres:
                include_genres.append(18)
            mood = 'emotional'
        if 'lighter' in tone_modifiers:
            if 35 not in include_genres:
                include_genres.append(35)
            mood = 'relaxed'
        return include_genres, mood
    
    def _generate_response_message(
        self,
        request_type: RequestType,
        media_type: Optional[MediaType],
        include_genres: List[int],
        exclude_genres: List[int],
        mood: Optional[str] = None,
        emotional_sub_intent: Optional[str] = None,
        tone_modifiers: List[str] = None,
        provider_name: Optional[str] = None,
        raw_user_message: str = ""
    ) -> str:
        """Generate a natural, witty, context-aware Scout response message."""
        tone_modifiers = tone_modifiers or []
        user_lower = raw_user_message.lower() if raw_user_message else ""
        media_str = "TV series" if media_type == MediaType.TV else ("movies" if media_type == MediaType.MOVIE else "picks")
        
        if request_type == RequestType.CHAT:
            if any(w in user_lower for w in ["heyyy", "hey", "hi", "hello", "sup", "yo"]):
                return "Hey there! Ready to dig into some cinema? Tell me what kind of mood or story you're feeling."
            return "Always here for movie talk! Tell me what vibe or genre you're craving."
        
        if request_type == RequestType.CONSTRAINT_ONLY:
            if exclude_genres:
                excluded_names = [GENRE_MAP.get(gid, "") for gid in exclude_genres if gid in GENRE_MAP]
                ex_str = ", ".join(filter(None, excluded_names))
                return f"Got it — leaving out {ex_str}. Here are fresh {media_str} that steer completely clear of that."
            if media_type == MediaType.TV:
                return "Locked in on TV series only. Let's see what's worthy of your screen."
            elif media_type == MediaType.MOVIE:
                return "Sticking purely to films! Here are standout movie picks."
            return f"Filter applied! Updating your {media_str}."
        
        if request_type == RequestType.CORRECTION:
            if media_type == MediaType.TV:
                return "Switching tracks to TV shows only! Here are gripping series to dive into."
            elif media_type == MediaType.MOVIE:
                return "Got it, movies only this time! Here are feature films that hit the mark."
            return f"Course corrected! Let's pull some fresh {media_str} for you."
        
        if request_type == RequestType.REFINEMENT:
            if emotional_sub_intent == "tearjerker" or any(w in user_lower for w in ["cry", "sobbing", "tears", "bawl"]):
                return "Tissues at the ready. We're pivoting straight to true, earned tearjerkers that don't hold back."
            elif emotional_sub_intent == "bittersweet":
                return "Leaning into the bittersweet side — beautiful, wistful stories that stay with you."
            elif emotional_sub_intent in ("hopeful", "cathartic"):
                return "Shifting towards hope and catharsis. These stories will lift you back up."
            elif tone_modifiers:
                return f"Dialing in a {tone_modifiers[0]} tone for you. Let's adjust the playlist."
            return f"Fine-tuning your picks! Here's a refined batch of {media_str}."
        
        # Fresh search
        if provider_name:
            if include_genres:
                genre_names = [GENRE_MAP.get(gid, "") for gid in include_genres[:2] if gid in GENRE_MAP]
                genre_str = " & ".join(filter(None, genre_names))
                return f"Scanning {provider_name} for top-notch {genre_str} {media_str} — here are the ones worth your time."
            return f"Browsing {provider_name}'s catalog for stellar {media_str}!"
        
        if emotional_sub_intent == "tearjerker":
            return "Get ready to feel things. Here are deeply emotional, heart-wrenching stories that truly deliver."
        elif emotional_sub_intent == "bittersweet":
            return "Exploring that poignant, bittersweet territory — stories rich with nostalgia, longing, and warmth."
        elif emotional_sub_intent in ("hopeful", "cathartic"):
            return "Looking for emotional stories with a beacon of hope at the end. Here are inspiring journeys."
        elif emotional_sub_intent == "feelgood":
            return "Need something to warm your soul? Here are feel-good stories with genuine heart."
        elif emotional_sub_intent == "thought_provoking":
            return "Stories that demand reflection and linger long after the credits. Here are compelling, thought-provoking watches."
        elif emotional_sub_intent == "intense":
            return "Dialing up the emotional intensity — powerful drama with high human stakes."
        elif mood == "emotional":
            return "In the mood for real emotional depth? Here are stories driven by unforgettable human journeys."
        
        if include_genres:
            genre_names = [GENRE_MAP.get(gid, "") for gid in include_genres[:2] if gid in GENRE_MAP]
            genre_str = " & ".join(filter(None, genre_names))
            return f"Here are some standout {genre_str} {media_str} that should hit the sweet spot!"
        
        return f"Here are three top {media_str} hand-picked for your screen tonight!"


# Global instance
intent_parser = IntentParser()
