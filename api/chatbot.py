import os
import json
import re
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class VegShiftChatbot:
    def __init__(self):
        self.documents = []
        self.vectorizer = None
        self.tfidf_matrix = None
        self.use_gemini = False
        self.gemini_model = None
        
        # Initialize Gemini API if available and key is set
        if GEMINI_AVAILABLE:
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    # Use the correct model name - gemini-pro is more stable
                    self.gemini_model = genai.GenerativeModel('gemini-pro')
                    self.use_gemini = True
                    print("✓ Gemini API initialized successfully")
                except Exception as e:
                    print(f"⚠ Gemini API initialization failed: {e}. Falling back to TF-IDF.")
            else:
                print("ℹ GEMINI_API_KEY not set. Using TF-IDF retrieval only.")
        
        self._load_knowledge_base()

    # ── JSON → readable text converters ──────────────────────────────

    def _convert_crop_advisory(self, data: dict) -> str:
        lines = ["Crop Advisory — top-ranked crops by city:"]
        for city, info in data.items():
            top = info.get("ranked_crops", [])[:5]
            crops = ", ".join(
                f"{c['crop']} ({c['season']}, score {c['score']:.1f})"
                for c in top
            )
            zone = info.get("current_zone", "")
            lines.append(
                f"{city} (Köppen zone {zone}): recommended crops are {crops}. "
                f"5-year rainfall trend: {info.get('rain_trend_5yr', 'N/A')} mm, "
                f"temperature trend: {info.get('temp_trend_5yr', 'N/A'):.3f} °C/yr."
            )
        return "\n".join(lines)

    def _convert_irrigation_strategy(self, data: dict) -> str:
        lines = ["Irrigation Strategy — water stress levels and recommendations by city:"]
        for city, info in data.items():
            avoid = ", ".join(info.get("avoid_crops", []))
            recommended = ", ".join(info.get("recommended_crops", []))
            method = info.get("irrigation_method", "").replace("_", " ")
            window = info.get("optimal_sow_window", "")
            rsi = info.get("rsi_level", "")
            schemes = "; ".join(
                f"{k}: {v}" for k, v in info.get("govt_schemes", {}).items()
            )
            lines.append(
                f"{city}: water stress level is {rsi}. "
                f"Recommended irrigation method: {method}. "
                f"Optimal sowing window: {window}. "
                f"Crops to avoid due to water demand: {avoid}. "
                f"Recommended low-water crops: {recommended}. "
                f"Government schemes available: {schemes}."
            )
        return "\n".join(lines)

    def _convert_exploitation_risk(self, data: dict) -> str:
        lines = ["Exploitation Risk Index (ERI) — economic risk scores by city:"]
        for city, info in data.items():
            eri = info.get("eri", 0)
            alert = "HIGH ALERT" if info.get("alert") else "within normal range"
            components = info.get("eri_components", {})
            comp_str = ", ".join(f"{k.replace('_', ' ')}: {v:.3f}" for k, v in components.items())
            primary = info.get("primary_crop", "")
            msp = info.get("msp_inr_per_quintal", "")
            distress = info.get("distress_price_threshold", "")
            alts = ", ".join(info.get("alternative_crops", []))
            procurement = info.get("procurement_center", "")
            lines.append(
                f"{city}: ERI score is {eri:.3f} — {alert}. "
                f"Risk components — {comp_str}. "
                f"Primary crop: {primary}, MSP ₹{msp}/quintal, distress threshold ₹{distress}/quintal. "
                f"Alternative crops if primary fails: {alts}. "
                f"Procurement: {procurement}."
            )
        return "\n".join(lines)

    def _convert_shap(self, data: dict) -> str:
        lines = ["SHAP Feature Importance — factors driving crop viability loss predictions:"]
        for entry in data.get("global_importance", []):
            feature = entry["feature"].replace("_", " ")
            score = entry["mean_abs_shap"]
            lines.append(f"  - {feature}: mean |SHAP| = {score:.4f}")
        city_shap = data.get("city_crop_shap", {})
        if city_shap:
            lines.append("\nTop SHAP drivers by city and crop:")
            for city, crops in list(city_shap.items())[:5]:
                for crop, features in list(crops.items())[:1]:
                    top_f = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
                    top_str = ", ".join(f"{k.replace('_',' ')}: {v:+.3f}" for k, v in top_f)
                    lines.append(f"  {city} / {crop}: {top_str}")
        return "\n".join(lines)

    def _convert_baseline_metrics(self, data: dict) -> str:
        lines = ["Baseline Model Performance Metrics:"]
        for model_name, metrics in data.items():
            auc = metrics.get("auc", "N/A")
            report = metrics.get("classification_report", {})
            acc = report.get("accuracy", "N/A")
            lines.append(
                f"  {model_name.replace('_', ' ').title()}: "
                f"accuracy {float(acc):.1%}, AUC {float(auc):.3f}."
            )
        return "\n".join(lines)

    def _convert_viability_trends(self, data: list) -> str:
        lines = ["Crop Viability Trend Report — statistical trend analysis per city and crop:"]
        for entry in data:
            city = entry.get("city", "")
            crop = entry.get("crop", "")
            trend = entry.get("trend", "")
            slope = entry.get("slope", 0)
            r2 = entry.get("r_squared", 0)
            p = entry.get("p_value", 1)
            sig = "statistically significant" if p < 0.05 else "not statistically significant"
            lines.append(
                f"{city} — {crop}: trend is {trend} "
                f"(slope {slope:+.5f}/yr, R²={r2:.3f}, {sig})."
            )
        return "\n".join(lines)

    def _convert_viability_events(self, data: list) -> str:
        lines = ["Crop Viability Loss Events (CVLE) — years when crops became unviable:"]
        by_city: Dict[str, list] = {}
        for entry in data:
            city = entry.get("city", "")
            by_city.setdefault(city, []).append(entry)
        for city, events in by_city.items():
            event_strs = []
            for e in events:
                event_strs.append(
                    f"{e['year']} ({e['crop']}, zone {e['koppen_zone']}, "
                    f"water deficit {e['crop_water_deficit']:.2f})"
                )
            lines.append(f"{city}: viability loss events in {'; '.join(event_strs)}.")
        return "\n".join(lines)

    def _convert_transition_report(self, data: list) -> str:
        lines = ["Climate Zone Transition Report — detected Köppen zone shifts by city:"]
        by_city: Dict[str, list] = {}
        for entry in data:
            city = entry.get("city", "")
            by_city.setdefault(city, []).append(entry)
        for city, transitions in by_city.items():
            t_strs = [
                f"{t['transition_year']}: {t['from_zone']} → {t['to_zone']} "
                f"(confirmed over {t['years_confirmed']} years)"
                for t in transitions
            ]
            lines.append(f"{city}: {'; '.join(t_strs)}.")
        return "\n".join(lines)

    def _json_to_text(self, filename: str, data) -> str:
        name = os.path.basename(filename)
        converters = {
            "crop_advisory.json":          lambda d: self._convert_crop_advisory(d),
            "irrigation_strategy.json":    lambda d: self._convert_irrigation_strategy(d),
            "exploitation_risk_report.json": lambda d: self._convert_exploitation_risk(d),
            "shap_explanation.json":       lambda d: self._convert_shap(d),
            "baseline_metrics.json":       lambda d: self._convert_baseline_metrics(d),
            "viability_trend_report.json": lambda d: self._convert_viability_trends(d),
            "crop_viability_events.json":  lambda d: self._convert_viability_events(d),
            "transition_report.json":      lambda d: self._convert_transition_report(d),
        }
        converter = converters.get(name)
        if converter:
            try:
                return converter(data)
            except Exception as e:
                print(f"Converter error for {name}: {e}")
        # Fallback: still better than raw JSON — flatten key/value pairs into sentences
        return self._flatten_json(data)

    def _flatten_json(self, obj, prefix="") -> str:
        parts = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                parts.append(self._flatten_json(v, f"{prefix}{k.replace('_',' ')} "))
        elif isinstance(obj, list):
            for item in obj:
                parts.append(self._flatten_json(item, prefix))
        else:
            parts.append(f"{prefix.strip()}: {obj}.")
        return " ".join(parts)

    # ── Knowledge base loading ────────────────────────────────────────

    def _load_knowledge_base(self):
        docs_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
        data_output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'output')

        doc_files = [
            'explanation.md',
            'LAYMAN_GUIDE.md',
            'MENTOR_SUMMARY.md',
            'READING_ROADMAP.md',
            'instructions.md',
            'data_flow.md',
        ]

        for doc_file in doc_files:
            file_path = os.path.join(docs_dir, doc_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.documents.append({
                            'content': f.read(),
                            'source': f'docs/{doc_file}',
                            'type': 'documentation',
                        })
                except Exception as e:
                    print(f"Error loading {doc_file}: {e}")

        output_files = [
            'baseline_metrics.json',
            'crop_advisory.json',
            'crop_viability_events.json',
            'exploitation_risk_report.json',
            'irrigation_strategy.json',
            'shap_explanation.json',
            'transition_report.json',
            'viability_trend_report.json',
        ]

        for output_file in output_files:
            file_path = os.path.join(data_output_dir, output_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    content = self._json_to_text(output_file, data)
                    self.documents.append({
                        'content': content,
                        'source': f'output/{output_file}',
                        'type': 'output_data',
                    })
                except Exception as e:
                    print(f"Error loading {output_file}: {e}")

        if self.documents:
            self.vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
            self.tfidf_matrix = self.vectorizer.fit_transform(
                [doc['content'] for doc in self.documents]
            )

    # ── Query handling ────────────────────────────────────────────────

    def _extract_relevant_sentences(self, content: str, query: str, max_sentences: int = 5) -> str:
        query_terms = set(query.lower().split())
        raw = re.split(r'(?<=[.!?])\s+|\n', content)
        sentences = [s.strip() for s in raw if len(s.strip()) > 20]

        scored = []
        for s in sentences:
            words = set(s.lower().split())
            score = len(query_terms & words)
            scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        return ' '.join(s for _, s in scored[:max_sentences] if s)

    def get_response(self, query: str, history: List[Dict[str, str]] | None = None) -> Dict[str, str]:
        """
        Get chatbot response using Gemini API (preferred) or TF-IDF fallback.
        Gemini is used for semantic understanding and contextual responses.
        TF-IDF is used as fallback for keyword matching or when Gemini unavailable.
        """
        if not self.documents:
            return {
                'response': "I don't have access to the knowledge base right now. Please try again later.",
                'source': 'system',
            }

        # Try Gemini first if available
        if self.use_gemini and self.gemini_model:
            try:
                return self._get_gemini_response(query, history)
            except Exception as e:
                print(f"Gemini error, falling back to TF-IDF: {e}")
                # Fall through to TF-IDF
        
        # Fall back to TF-IDF
        return self._get_tfidf_response(query, history)

    def _get_gemini_response(self, query: str, history: List[Dict[str, str]] | None = None) -> Dict[str, str]:
        """Use Gemini API for intelligent response generation."""
        # Retrieve context from knowledge base
        context_docs = self._retrieve_context_docs(query, history, top_k=3)
        
        if not context_docs:
            return {
                'response': (
                    "I couldn't find specific information about that. "
                    "Try asking about crop advisories, irrigation strategies, "
                    "risk scores, SHAP explanations, or city-level climate data."
                ),
                'source': 'system',
            }
        
        # Build context from retrieved documents
        context = "\n".join([doc['content'][:500] for doc in context_docs])
        sources = ', '.join([doc['source'] for doc in context_docs])
        
        # Build conversation history for context
        conv_history = ""
        if history:
            for msg in history[-4:]:  # Use last 4 messages for context
                role = "User" if msg.get('isUser') else "Assistant"
                conv_history += f"{role}: {msg['text']}\n"
        
        # Create prompt for Gemini
        system_prompt = """You are VegShift, an AI assistant for Indian agriculture helping farmers understand crop viability, climate change, and irrigation strategies. 
Your knowledge comes from detailed analysis of 10 Indian cities (Ahmedabad, Bangalore, Chennai, Delhi, Hyderabad, Jaipur, Kolkata, Lucknow, Mumbai, Pune).

Answer questions concisely and conversationally. Reference specific data and city examples from the knowledge base.
Focus on actionable insights for farmers. Be friendly and encouraging."""

        prompt = f"""{system_prompt}

Knowledge Base Context:
{context}

Conversation History:
{conv_history}

User Question: {query}

Provide a helpful, specific answer based on the knowledge base context. Keep it under 200 words."""

        try:
            response = self.gemini_model.generate_content(prompt)
            return {
                'response': response.text or "I couldn't generate a response. Please try again.",
                'source': sources,
            }
        except Exception as e:
            raise Exception(f"Gemini generation failed: {str(e)}")

    def _retrieve_context_docs(self, query: str, history: List[Dict[str, str]] | None = None, top_k: int = 3) -> List[Dict]:
        """Retrieve relevant documents using TF-IDF for context."""
        if not self.documents or self.vectorizer is None:
            return []
        
        augmented_query = query
        if history:
            last_user = next((m['text'] for m in reversed(history) if m.get('isUser')), None)
            if last_user and last_user != query:
                augmented_query = f"{last_user} {query}"
        
        query_vector = self.vectorizer.transform([augmented_query])
        similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]
        
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [self.documents[i] for i in top_indices if similarities[i] > 0.05]

    def _get_tfidf_response(self, query: str, history: List[Dict[str, str]] | None = None) -> Dict[str, str]:
        """Fallback TF-IDF response generation."""
        if not self.documents or self.vectorizer is None:
            return {
                'response': "I don't have access to the knowledge base right now. Please try again later.",
                'source': 'system',
            }

        augmented_query = query
        if history:
            last_user = next((m['text'] for m in reversed(history) if m.get('isUser')), None)
            if last_user and last_user != query:
                augmented_query = f"{last_user} {query}"

        query_vector = self.vectorizer.transform([augmented_query])
        similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]

        top_indices = np.argsort(similarities)[-3:][::-1]
        top_docs = [self.documents[i] for i in top_indices if similarities[i] > 0.05]

        if not top_docs:
            return {
                'response': (
                    "I couldn't find specific information about that. "
                    "Try asking about crop advisories, irrigation strategies, "
                    "risk scores, SHAP explanations, or city-level climate data."
                ),
                'source': 'system',
            }

        response_parts = []
        sources = []

        for doc in top_docs[:2]:
            relevant = self._extract_relevant_sentences(doc['content'], query, max_sentences=4)
            if relevant:
                response_parts.append(relevant)
            sources.append(doc['source'])

        response = ' '.join(response_parts)
        if len(response) > 1200:
            response = response[:1197] + '…'

        return {
            'response': response,
            'source': ', '.join(dict.fromkeys(sources)),
        }


# Global chatbot instance
chatbot = VegShiftChatbot()
