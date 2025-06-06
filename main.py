import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from urllib.parse import urljoin, urlparse
import unittest
from unittest.mock import patch, MagicMock, call
import sys
from io import StringIO

class WebCrawler:
    def __init__(self):
        self.index = defaultdict(list)
        self.visited = set()

    def crawl(self, url, base_url=None):
        if url in self.visited:
            return
        self.visited.add(url)

        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            self.index[url] = soup.get_text()

            for link in soup.find_all('a'):
                href = link.get('href')
                if href:
                    # Handle relative URLs (e.g., /about)
                    if not urlparse(href).netloc:
                        full_url = urljoin(url, href)
                    else:
                        full_url = href

                    # Only follow links to the same domain
                    base = base_url or url
                    if full_url.startswith(base):
                        self.crawl(full_url, base_url=base)
        except Exception as e:
            print(f"Error crawling {url}: {e}")

    def search(self, keyword):
        results = []
        for url, text in self.index.items():
            if keyword.lower() in text.lower():
                results.append(url)
        return results

    def print_results(self, results):
        if results:
            print("Search results:")
            for result in results:
                print(f"- {result}")
        else:
            print("No results found.")

def main():
    crawler = WebCrawler()
    start_url = "https://example.com"
    crawler.crawl(start_url)

    keyword = "test"
    results = crawler.search(keyword)
    crawler.print_results(results)

class WebCrawlerTests(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.crawler = WebCrawler()
        
    def tearDown(self):
        """Clean up after each test method"""
        self.crawler = None
    
    def test_init(self):
        """Test initialization of WebCrawler class"""
        self.assertIsInstance(self.crawler.index, defaultdict)
        self.assertEqual(len(self.crawler.index), 0)
        self.assertIsInstance(self.crawler.visited, set)
        self.assertEqual(len(self.crawler.visited), 0)

    @patch('requests.get')
    def test_crawl_success(self, mock_get):
        """Test successful crawling with link discovery"""
        sample_html = """
        <html><body>
            <h1>Welcome!</h1>
            <a href="/about">About Us</a>
            <a href="https://www.external.com">External Link</a>
            <a href="/contact">Contact</a>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = sample_html
        mock_get.return_value = mock_response

        self.crawler.crawl("https://example.com")

        # Assert URLs are visited correctly
        self.assertIn("https://example.com", self.crawler.visited)
        self.assertIn("https://example.com/about", self.crawler.visited)
        self.assertIn("https://example.com/contact", self.crawler.visited)
        
        # Assert content is indexed correctly
        self.assertIn("https://example.com", self.crawler.index)
        
        # Assert external links are not crawled
        self.assertNotIn("https://www.external.com", self.crawler.visited)
        
        # Verify requests.get was called correctly
        mock_get.assert_any_call("https://example.com")
        mock_get.assert_any_call("https://example.com/about")
        mock_get.assert_any_call("https://example.com/contact")

    @patch('requests.get')
    def test_crawl_recursive(self, mock_get):
        """Test recursive crawling behavior with nested links"""
        # First level HTML
        first_level_html = """
        <html><body>
            <h1>Welcome!</h1>
            <a href="/about">About</a>
        </body></html>
        """
        
        # Second level HTML (about page)
        second_level_html = """
        <html><body>
            <h1>About Us</h1>
            <a href="/team">Our Team</a>
        </body></html>
        """
        
        def mock_get_response(url):
            mock_resp = MagicMock()
            if url == "https://example.com":
                mock_resp.text = first_level_html
            elif url == "https://example.com/about":
                mock_resp.text = second_level_html
            else:
                mock_resp.text = "<html><body>Content</body></html>"
            return mock_resp
            
        mock_get.side_effect = mock_get_response
        
        self.crawler.crawl("https://example.com")
        
        # Verify all pages were visited
        self.assertIn("https://example.com", self.crawler.visited)
        self.assertIn("https://example.com/about", self.crawler.visited)
        self.assertIn("https://example.com/team", self.crawler.visited)

    @patch('requests.get')
    def test_crawl_with_cycle(self, mock_get):
        """Test crawling with cyclic references to ensure no infinite loops"""
        cyclic_html = """
        <html><body>
            <h1>Welcome!</h1>
            <a href="/">Home</a>
            <a href="/about">About</a>
        </body></html>
        """
        
        def mock_get_response(url):
            mock_resp = MagicMock()
            mock_resp.text = cyclic_html
            return mock_resp
            
        mock_get.side_effect = mock_get_response
        
        self.crawler.crawl("https://example.com")
        
        # Each URL should only be visited once despite cyclic links
        # We expect 3 calls: example.com, example.com/ (home), and example.com/about
        self.assertEqual(mock_get.call_count, 3)

    @patch('requests.get')
    def test_crawl_error_handling(self, mock_get):
        """Test error handling during crawling"""
        # First URL raises an exception
        mock_get.side_effect = requests.exceptions.RequestException("Test Error")
        
        # Capture print output
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            self.crawler.crawl("https://example.com")
            
            # Verify the error was logged correctly
            self.assertIn("Error crawling https://example.com", captured_output.getvalue())
            self.assertIn("Test Error", captured_output.getvalue())
            
            # Verify the URL was still marked as visited to prevent retry
            self.assertIn("https://example.com", self.crawler.visited)
        finally:
            sys.stdout = sys.__stdout__  # Restore stdout

    @patch('requests.get')
    def test_crawl_connection_timeout(self, mock_get):
        """Test handling of connection timeout errors"""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            self.crawler.crawl("https://example.com")
            self.assertIn("Error crawling https://example.com", captured_output.getvalue())
            self.assertIn("Connection timed out", captured_output.getvalue())
        finally:
            sys.stdout = sys.__stdout__

    def test_search_match(self):
        """Test search functionality with matching keyword"""
        self.crawler.index["page1"] = "This has the keyword in content"
        self.crawler.index["page2"] = "No matching text here"
        
        results = self.crawler.search("keyword")
        self.assertEqual(results, ["page1"])

    def test_search_case_insensitive(self):
        """Test case-insensitive search"""
        self.crawler.index["page1"] = "This has the KEYWORD in content"
        self.crawler.index["page2"] = "Another KeyWord is here"
        self.crawler.index["page3"] = "No matching text"
        
        results = self.crawler.search("keyword")
        self.assertIn("page1", results)
        self.assertIn("page2", results)
        self.assertEqual(len(results), 2)

    def test_search_empty_index(self):
        """Test search on empty index"""
        results = self.crawler.search("keyword")
        self.assertEqual(results, [])

    def test_search_no_match(self):
        """Test search with no matching results"""
        self.crawler.index["page1"] = "Content without match"
        self.crawler.index["page2"] = "More unrelated content"
        
        results = self.crawler.search("keyword")
        self.assertEqual(results, [])

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_results_with_matches(self, mock_stdout):
        """Test printing with matching results"""
        results = ["https://test.com/result1", "https://test.com/result2"]
        self.crawler.print_results(results)
        
        output = mock_stdout.getvalue()
        self.assertIn("Search results:", output)
        self.assertIn("- https://test.com/result1", output)
        self.assertIn("- https://test.com/result2", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_results_no_matches(self, mock_stdout):
        """Test printing with no results"""
        self.crawler.print_results([])
        
        output = mock_stdout.getvalue()
        self.assertIn("No results found.", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_results_empty_url(self, mock_stdout):
        """Test printing with empty URL string"""
        self.crawler.print_results([""])
        
        output = mock_stdout.getvalue()
        self.assertIn("Search results:", output)
        self.assertIn("- ", output)

if __name__ == "__main__":
    unittest.main()  # Run unit tests
    # main()  # Run your main application logic 

# Uncomment to run the application rather than tests
# if __name__ == "__main__":
#     main()
