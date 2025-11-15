import scrapy


class Motos2023_2025Spider(scrapy.Spider):
    name = "motos_2023_2025"
    allowed_domains = ["bikez.com"]

    start_urls = [
        "https://bikez.com/year/2023-motorcycle-models.php",
        "https://bikez.com/year/2024-motorcycle-models.php",
        "https://bikez.com/year/2025-motorcycle-models.php",
    ]

    def parse(self, response):

        links = response.css("a::attr(href)").getall()

        model_links = [l for l in links if "motorcycles" in l.lower()]

        for link in model_links[:20]:
            url = response.urljoin(link)
            yield scrapy.Request(url, callback=self.parse_moto)

    def parse_moto(self, response):

        def get_spec(label):
    
            xpath = (
                f"//tr[td[1][contains(translate(normalize-space(), "
                f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                f"'{label.lower()}')]]/td[2]/text()"
            )
            return (
                response.xpath(xpath).get(default="Unknown").strip()
            )

        title = response.css("h1::text").get(default="Unknown").strip()

        yield {
            "Brand": get_spec("make"),
            "Model": title.replace("specifications", "").strip(),
            "Year": get_spec("year"),
            "Category": get_spec("category"),
            "Displacement (ccm)": get_spec("displacement").replace("ccm", "").strip(),
            "Power (hp)": get_spec("power").replace("hp", "").strip(),
            "Fuel capacity (lts)": get_spec("fuel capacity").replace("litres", "").strip(),
            "Dry weight (kg)": get_spec("dry weight").replace("kg", "").strip(),
            "Seat height (mm)": get_spec("seat height").replace("mm", "").strip(),
            "Torque (Nm)": get_spec("torque").replace("nm", "").strip(),
            "Cooling system": get_spec("cooling system"),
            "Transmission type": get_spec("transmission"),
            "Gearbox": get_spec("gearbox"),
            "Engine stroke": get_spec("engine stroke"),
            "Engine cylinder": get_spec("engine cylinder"),
        }
