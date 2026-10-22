"""
Test script to measure Scout's actual latency with live Gemini API.
This will help identify performance bottlenecks.
"""

import asyncio
import time
import json
import pytest
from services.scout_service import scout_service


@pytest.mark.asyncio
async def test_scout_latency():
    """Test Scout with actual Gemini API and TMDB calls."""
    
    test_messages = [
        ("Hey there!", "Greeting (should be fast, no search)"),
        ("sci-fi movies and TV shows with sad ending", "Mixed media request with both types"),
        ("Something fun for tonight", "Simple recommendation request"),
    ]
    
    print("="*80)
    print("SCOUT LATENCY TEST")
    print("="*80)
    
    if not scout_service.gemini_configured:
        print("\n❌ Gemini API not configured. Set GEMINI_API_KEY in backend/.env")
        return
    
    print("\n✓ Gemini API configured")
    print(f"✓ Model: {scout_service._get_client()}")
    print("\n" + "="*80 + "\n")
    
    for message, description in test_messages:
        print(f"\nTest: {description}")
        print(f"Message: '{message}'")
        print("-" * 80)
        
        start = time.time()
        try:
            result = await scout_service.process_message(
                user_message=message,
                conversation_history=[]
            )
            
            elapsed = time.time() - start
            
            print(f"\n✓ Success in {elapsed*1000:.0f}ms")
            print(f"  Intent: {result.get('intent', 'unknown')}")
            print(f"  Message: {result['message'][:80]}...")
            print(f"  Recommendations: {len(result.get('recommendations', []))}")
            
            if result.get('recommendations'):
                media_types = [r.get('media_type') for r in result['recommendations']]
                print(f"  Media types: {media_types}")
                print(f"  Titles: {[r['title'][:30] for r in result['recommendations'][:3]]}")
            
            # Analyze performance
            if elapsed < 2.0:
                print(f"  Performance: ✓ Excellent ({elapsed*1000:.0f}ms)")
            elif elapsed < 4.0:
                print(f"  Performance: ⚠️  Acceptable ({elapsed*1000:.0f}ms)")
            else:
                print(f"  Performance: ❌ Too slow ({elapsed*1000:.0f}ms)")
                
        except Exception as e:
            elapsed = time.time() - start
            print(f"\n❌ Failed in {elapsed*1000:.0f}ms")
            print(f"  Error: {type(e).__name__}: {str(e)}")
        
        print("\n" + "="*80)
        
        # Small delay between requests
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(test_scout_latency())
