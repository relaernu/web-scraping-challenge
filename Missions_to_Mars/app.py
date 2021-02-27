from flask import Flask, redirect, render_template
import scraping

app = Flask(__name__)

@app.route("/")
def home():
    mars_dict = scraping.getlatestdict()
    return render_template("index.html", mars_dict = mars_dict)

@app.route("/scrape")
def scrape():
    from splinter import Browser
    from webdriver_manager.chrome import ChromeDriverManager
    executable_path = {'executable_path': ChromeDriverManager().install()}
    browser = Browser('chrome', **executable_path, headless=False)
    scraping.scrape(browser)
    browser.quit()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
    