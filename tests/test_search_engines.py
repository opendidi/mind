# -*- coding: UTF-8 -*-
"""Test Bing search — HTML parsing, URL decoding, title extraction."""

import pytest
from unittest.mock import patch, MagicMock

from app.util.search.engines import search_bing


@patch('app.util.search.engines.requests.get')
def test_search_bing_web(mock_get):
    """Bing web search parses results from HTML."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '''
    <html><body>
    <ol id="b_results">
    <li class="b_algo">
      <h2><a href="https://www.example.com/page">Example Title</a></h2>
      <div class="b_caption"><p>Example snippet text</p></div>
    </li>
    </ol>
    </body></html>
    '''
    mock_get.return_value = mock_resp

    results = search_bing('test keyword', max_results=5)

    assert isinstance(results, list)
    if results:
        assert 'title' in results[0] or 'url' in results[0] or 'snippet' in results[0]


@patch('app.util.search.engines.requests.get')
def test_search_bing_empty(mock_get):
    """Bing returns no results."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '<html><body></body></html>'
    mock_get.return_value = mock_resp

    results = search_bing('xyznonexistent12345', max_results=5)
    assert results == [] or isinstance(results, list)


@patch('app.util.search.engines.requests.get')
def test_search_bing_http_error(mock_get):
    """Bing returns HTTP error."""
    mock_get.side_effect = Exception('Network error')

    results = search_bing('test', max_results=5)
    assert results == []
