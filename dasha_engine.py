from datetime import timedelta, datetime

DAYS_PER_YEAR = 365.25
NAKSHATRA_SIZE = 360 / 27

PLANET_SEQUENCE = [
    ("Ketu", 7),
    ("Venus", 20),
    ("Sun", 6),
    ("Moon", 10),
    ("Mars", 7),
    ("Rahu", 18),
    ("Jupiter", 16),
    ("Saturn", 19),
    ("Mercury", 17),
]

NAKSHATRA_LORD_MAP = [
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"
] * 3


class VimshottariDasha:

    def __init__(self, birth_datetime_utc, nak_index, deg_in_nak, depth=5):
        self.birth = birth_datetime_utc
        self.nak_index = nak_index
        self.deg_in_nak = deg_in_nak
        self.depth = max(1, min(depth, 5))  # Allow up to Prana


    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _rotated_sequence(self, start_planet):
        names = [p[0] for p in PLANET_SEQUENCE]
        idx = names.index(start_planet)
        return PLANET_SEQUENCE[idx:] + PLANET_SEQUENCE[:idx]

    def _find_starting_lord(self):
        return NAKSHATRA_LORD_MAP[self.nak_index]


    # ---------------------------------------------------------
    # Recursive Generator
    # ---------------------------------------------------------

    def _generate_level(self, start_dt, parent_days, parent_planet, level):

        if level > self.depth:
            return None

        segments = []
        cursor = start_dt
        sequence = self._rotated_sequence(parent_planet)

        for name, years in sequence:

            proportion = years / 120
            child_days = parent_days * proportion
            end_dt = cursor + timedelta(days=child_days)

            node = {
                "planet": name,
                "start": cursor.isoformat(),
                "end": end_dt.isoformat()
            }

            next_level = self._generate_level(
                cursor,
                child_days,
                name,
                level + 1
            )

            if next_level:
                if level == 2:
                    node["pratyantardashas"] = next_level
                elif level == 3:
                    node["sukshma_dashas"] = next_level
                elif level == 4:
                    node["prana_dashas"] = next_level

            segments.append(node)
            cursor = end_dt

        return segments


    # ---------------------------------------------------------
    # Build Full Tree
    # ---------------------------------------------------------

    def build_full_tree(self):

        md_list = []
        starting_lord = self._find_starting_lord()

        remaining_fraction = (NAKSHATRA_SIZE - self.deg_in_nak) / NAKSHATRA_SIZE
        cursor = self.birth

        first_years = dict(PLANET_SEQUENCE)[starting_lord]
        first_days = first_years * DAYS_PER_YEAR * remaining_fraction
        first_end = cursor + timedelta(days=first_days)

        first_node = {
            "planet": starting_lord,
            "start": cursor.isoformat(),
            "end": first_end.isoformat()
        }

        if self.depth > 1:
            first_node["antardashas"] = self._generate_level(
                cursor,
                first_days,
                starting_lord,
                2  # Correct level alignment
            )

        md_list.append(first_node)
        cursor = first_end

        full_sequence = self._rotated_sequence(starting_lord)

        for name, years in full_sequence[1:]:

            duration_days = years * DAYS_PER_YEAR
            end = cursor + timedelta(days=duration_days)

            node = {
                "planet": name,
                "start": cursor.isoformat(),
                "end": end.isoformat()
            }

            if self.depth > 1:
                node["antardashas"] = self._generate_level(
                    cursor,
                    duration_days,
                    name,
                    2  # Correct level alignment
                )

            md_list.append(node)
            cursor = end

        return {"vimshottari": {"mahadashas": md_list}}


    # ---------------------------------------------------------
    # Current Running Dasha
    # ---------------------------------------------------------

    def get_current_dasha(self, full_tree):

        now = datetime.now(self.birth.tzinfo)

        result = {
            "mahadasha": None,
            "antardasha": None,
            "pratyantardasha": None,
            "sukshma_dasha": None,
            "prana_dasha": None
        }

        def parse(dt_str):
            return datetime.fromisoformat(dt_str)

        def clean(node):
            return {
                "planet": node["planet"],
                "start": node["start"],
                "end": node["end"]
            }

        mahadashas = full_tree["vimshottari"]["mahadashas"]

        for md in mahadashas:

            if parse(md["start"]) <= now < parse(md["end"]):

                result["mahadasha"] = clean(md)

                for ad in md.get("antardashas", []):

                    if parse(ad["start"]) <= now < parse(ad["end"]):

                        result["antardasha"] = clean(ad)

                        for pd in ad.get("pratyantardashas", []):

                            if parse(pd["start"]) <= now < parse(pd["end"]):

                                result["pratyantardasha"] = clean(pd)

                                for sd in pd.get("sukshma_dashas", []):

                                    if parse(sd["start"]) <= now < parse(sd["end"]):

                                        result["sukshma_dasha"] = clean(sd)

                                        for pr in sd.get("prana_dashas", []):

                                            if parse(pr["start"]) <= now < parse(pr["end"]):
                                                result["prana_dasha"] = clean(pr)
                                                break
                                        break
                                break
                        break
                break

        return result
