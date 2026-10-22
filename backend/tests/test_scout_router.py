"""
Tests for Scout chat router endpoint.

Tests the FastAPI endpoint with mocked Scout service.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app


client = TestClient(app)


class TestScoutChatEndpoint:
    """Test /api/scout/chat endpoint."""
    
    @patch('routers.scout.scout_service')
    def test_chat_success_with_recommendations(self, mock_service):
        """Test successful chat response with movie recommendations."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(return_value={
            "message": "Here are some great comedies!",
            "recommendations": [
                {
                    "id": 123,
                    "title": "Test Comedy",
                    "poster_path": "/test.jpg",
                    "vote_average": 7.5,
                    "release_date": "2024-01-15",
                    "explanation": "Perfect for a chill watch"
                }
            ]
        })
        
        response = client.post("/api/scout/chat", json={
            "message": "I want a comedy",
            "conversation_history": []
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Here are some great comedies!"
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["title"] == "Test Comedy"
    
    @patch('routers.scout.scout_service')
    def test_chat_success_without_recommendations(self, mock_service):
        """Test chat response with clarification (no recommendations)."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(return_value={
            "message": "Do you want action or comedy?",
            "recommendations": []
        })
        
        response = client.post("/api/scout/chat", json={
            "message": "Something fun",
            "conversation_history": []
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Do you want action or comedy?"
        assert len(data["recommendations"]) == 0
    
    @patch('routers.scout.scout_service')
    def test_chat_with_conversation_history(self, mock_service):
        """Test that conversation history is passed to service."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(return_value={
            "message": "Got it!",
            "recommendations": []
        })
        
        response = client.post("/api/scout/chat", json={
            "message": "Make it shorter",
            "conversation_history": [
                {"role": "user", "content": "I want a comedy"},
                {"role": "assistant", "content": "Here are some comedies!"}
            ]
        })
        
        assert response.status_code == 200
        # Verify service was called with history
        mock_service.process_message.assert_called_once()
        call_args = mock_service.process_message.call_args
        assert len(call_args[1]["conversation_history"]) == 2
    
    @patch('routers.scout.scout_service')
    def test_chat_unconfigured_returns_503(self, mock_service):
        """Test that unconfigured Scout returns 503 service unavailable."""
        mock_service.gemini_configured = False
        
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": []
        })
        
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()
    
    @patch('routers.scout.scout_service')
    def test_chat_configuration_error_returns_503(self, mock_service):
        """Test that configuration errors return 503."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(
            side_effect=ValueError("not configured")
        )
        
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": []
        })
        
        assert response.status_code == 503
    
    @patch('routers.scout.scout_service')
    def test_chat_rate_limit_returns_429(self, mock_service):
        """Test that rate limit errors return 429."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(
            side_effect=Exception("overwhelmed right now (API rate limit)")
        )
        
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": []
        })
        
        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()
    
    @patch('routers.scout.scout_service')
    def test_chat_timeout_returns_504(self, mock_service):
        """Test that timeout errors return 504."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(
            side_effect=Exception("Took too long to think")
        )
        
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": []
        })
        
        assert response.status_code == 504

    @patch('routers.scout.scout_service')
    def test_chat_timeout_in_value_error_returns_504(self, mock_service):
        """Test that upstream timeouts raised as ValueError return 504 instead of 400."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(
            side_effect=ValueError("Scout is taking a bit too long to think of recommendations")
        )
        
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": []
        })
        
        assert response.status_code == 504
        assert "too long" in response.json()["detail"].lower()
    
    @patch('routers.scout.scout_service')
    def test_chat_generic_error_returns_500(self, mock_service):
        """Test that generic errors return 500 with user-friendly message."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(
            side_effect=Exception("Something went sideways")
        )
        
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": []
        })
        
        assert response.status_code == 500
        # Should have user-friendly error message
        detail = response.json()["detail"]
        assert isinstance(detail, str)
        assert len(detail) > 0
    
    def test_chat_empty_message_returns_422(self):
        """Test that empty message is rejected."""
        response = client.post("/api/scout/chat", json={
            "message": "",
            "conversation_history": []
        })
        
        assert response.status_code == 422
    
    def test_chat_missing_message_returns_422(self):
        """Test that missing message field is rejected."""
        response = client.post("/api/scout/chat", json={
            "conversation_history": []
        })
        
        assert response.status_code == 422
    
    def test_chat_invalid_history_format_returns_422(self):
        """Test that invalid conversation history format is rejected."""
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": "not a list"
        })
        
        assert response.status_code == 422
    
    def test_chat_history_missing_role_returns_422(self):
        """Test that history messages without role are rejected."""
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": [
                {"content": "Missing role field"}
            ]
        })
        
        assert response.status_code == 422


class TestScoutHealthEndpoint:
    """Test /api/scout/health endpoint."""
    
    @patch('routers.scout.scout_service')
    def test_health_check_configured(self, mock_service):
        """Test health check when Scout is configured."""
        mock_service.gemini_configured = True
        
        response = client.get("/api/scout/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "model" in data
        assert "tmdb_configured" in data
        assert data["configured"] == True
    
    @patch('routers.scout.scout_service')
    def test_health_check_unconfigured(self, mock_service):
        """Test health check when Scout is not configured."""
        mock_service.gemini_configured = False
        
        response = client.get("/api/scout/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] == False


class TestScoutResponseValidation:
    """Test that Scout responses match frontend contract."""
    
    @patch('routers.scout.scout_service')
    def test_response_has_required_fields(self, mock_service):
        """Test that response includes all required fields."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(return_value={
            "message": "Test message",
            "recommendations": []
        })
        
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": []
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields per Scout.jsx contract
        assert "message" in data
        assert "recommendations" in data
        assert isinstance(data["message"], str)
        assert isinstance(data["recommendations"], list)
    
    @patch('routers.scout.scout_service')
    def test_recommendation_has_required_fields(self, mock_service):
        """Test that recommendations include fields expected by PosterCard."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(return_value={
            "message": "Test",
            "recommendations": [{
                "id": 123,
                "title": "Test Movie",
                "poster_path": "/test.jpg",
                "vote_average": 7.5,
                "release_date": "2024-01-15",
                "explanation": "Test explanation"
            }]
        })
        
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": []
        })
        
        assert response.status_code == 200
        movie = response.json()["recommendations"][0]
        
        # Fields expected by frontend PosterCard component
        assert "id" in movie
        assert "title" in movie
        assert "poster_path" in movie
        # Scout-specific field
        assert "explanation" in movie
    
    @patch('routers.scout.scout_service')
    def test_recommendation_optional_fields_nullable(self, mock_service):
        """Test that optional fields can be null."""
        mock_service.gemini_configured = True
        mock_service.process_message = AsyncMock(return_value={
            "message": "Test",
            "recommendations": [{
                "id": 123,
                "title": "Test Movie",
                "poster_path": None,  # Optional
                "vote_average": None,  # Optional
                "release_date": None,  # Optional
                "explanation": None  # Optional
            }]
        })
        
        response = client.post("/api/scout/chat", json={
            "message": "Test",
            "conversation_history": []
        })
        
        assert response.status_code == 200
        movie = response.json()["recommendations"][0]
        assert movie["id"] == 123
        assert movie["title"] == "Test Movie"
