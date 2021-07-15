import hashlib
import queue
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from functools import wraps
from pathlib import Path
from typing import Literal, Optional

import requests

from __init__ import DEBUG, config, logging
from server import otp_queue, run_app

SECRET = config["auth"]["secret"]
BASE_URL = "https://cdn-api.co-vin.in/api/v2"
HEADERS = {'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1)')}
MAX_ERROR_RETRY = 5


class OtpError(Exception):
    def __str__(self) -> str:
        return "Failed to get otp from user"


def get_otp():
    """Gets otp from otp_queue"""
    # TODO: Allow multiple methods to get_otp (eg: a telegram message)
    # all that needs to be modified is giving the otp_queue to that module
    try:
        return otp_queue.get(timeout=180)
    except queue.Empty:
        raise OtpError


class CowinAuth:
    TOKEN_PATH = Path("api_token.txt")
    OTP_GENERATE_URL = BASE_URL + "/auth/generateMobileOTP"
    OTP_VALIDATE_URL = BASE_URL + "/auth/validateMobileOtp"  # seriously bro, wtf?

    def __init__(self, mobile: str):
        self.mobile = mobile
        if (
            self.TOKEN_PATH.exists()
            and time.time() - self.TOKEN_PATH.stat().st_atime < 3600
        ):
            logging.info("Reading saved token from file")
            self.token = self.TOKEN_PATH.read_text()
        else:
            self.token = self.refresh_token()
    
    def refresh_token(self):
        # TODO: add rate limits, measure timing, etc.
        # right now we depend on timeout of otp_queue.get
        logging.info("Refreshing token")
        for _ in range(MAX_ERROR_RETRY):
            try:
                # FIXME: This can this also raise HTTPError
                return self._fetch_token()
            except OtpError as e:
                logging.error(e)

        logging.critical("Failed to get otp!")
        raise OtpError

    def _fetch_token(self):
        logging.info("Fetching new token")    
        otp_data = self.generate_otp(self.mobile)
        otp = get_otp()
        self.token = self.validate_otp(otp, otp_data["txnId"])["token"]
        self.TOKEN_PATH.write_text(self.token)
        return self.token

    def generate_otp(self, mobile) -> dict:
        """Make POST request to generate otp giving mobile and secret as json"""
        data = {"mobile": mobile, "secret": SECRET}
        r = requests.post(self.OTP_GENERATE_URL, headers=HEADERS, json=data)
        return r.json()

    def validate_otp(self, otp: str, txnId: str):
        """Make POST request to validate otp"""
        # get sha256 hash of otp
        hashed = hashlib.sha256(otp.encode("utf-8")).hexdigest()
        data = {"otp": hashed, "txnId": txnId}
        r = requests.post(self.OTP_VALIDATE_URL, headers=HEADERS, json=data)
        return r.json()


@dataclass
class Requirements:
    vaccine_type: Literal["ANY", "COVISHIELD", "COVAXIN", "SPUTNIK"] = "ANY"
    min_age: Literal[18, 45] = 18
    dose_seq: Literal[1, 2] = 1
    fee_type: Literal["ANY", "Free", "Paid"] = "ANY"
    preferred_centers: tuple[str, ...] = tuple()

    def __post_init__(self):
        self._preferred_center_matchers = tuple(
            SequenceMatcher(None, center) for center in self.preferred_centers)

    def center_name_score(self, center_name: str):
        """Checks if given center_name is a preferred center"""
        # TOOD: This computation can be cached
        # TODO: Current API treats preferred_centers like an unordered set
        #       rather than an ordered list. We could also return index of max match
        ratios = []
        for matcher in self._preferred_center_matchers:
            matcher.set_seq2(center_name)
            ratios.append(matcher.ratio())
        return max(ratios, default=0)


def refresh_and_retry_on_error(fn):
    """Decorator for methods of CowinApi that calls refresh_token on auth error"""
    @wraps(fn)
    def func(self: "CowinApi", *args, **kwargs):
        for i in range(MAX_ERROR_RETRY):
            try:
                return fn(self, *args, **kwargs)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403 or e.response.status_code == 401:
                    logging.error(f"Api error! {e!s}")
                    if i > 0:  # if it's not the first time
                        logging.info("Sleeping for a few seconds")
                        time.sleep(4 ** i)
                    self.refresh_token()
                else:
                    # TODO: Handle other errors gracefully instead of crashing
                    raise e
        raise Exception("Failed to call api")
    return func


class CowinApi:
    SESSIONS_BY_PIN_URL = BASE_URL + "/appointment/sessions/findByPin"
    BENEFICIARIES_URL = BASE_URL + "/appointment/beneficiaries"
    SCHEDULE_APPOINTMENT_URL = BASE_URL + "/appointment/schedule"

    def __init__(self, auth: Optional[CowinAuth]) -> None:
        # TODO: auth == None is untested
        self.sess = requests.Session()
        self.sess.headers.update(HEADERS)
        self.auth = auth
        if auth is None:
            self.SESSIONS_BY_PIN_URL = self.SESSIONS_BY_PIN_URL.replace(
                "/sessions", "/public/sessions")
        else:
            self.sess.headers.update(self.header)

    def refresh_token(self):
        assert self.auth is not None
        self.auth.refresh_token()
        self.sess.headers.update(self.header)
    
    @property
    def header(self):
        assert self.auth is not None
        return {"Authorization": "Bearer " + self.auth.token, 
                "content-type": "application/json"}

    @refresh_and_retry_on_error
    def get_sessions_by_pincode(self, pincode, date) -> dict:
        """Make GET request to get sessions by pincode and date"""
        data = {"pincode": pincode, "date": date}
        r = self.sess.get(self.SESSIONS_BY_PIN_URL, params=data)
        r.raise_for_status()
        return r.json()

    @refresh_and_retry_on_error
    def get_beneficiaries(self) -> dict:
        """Make GET request to get beneficiaries"""
        r = self.sess.get(self.BENEFICIARIES_URL)
        r.raise_for_status()
        return r.json()

    @refresh_and_retry_on_error
    def book_session(self, session, beneficiaries, reqs: Requirements):
        data = {
            "dose": reqs.dose_seq,
            "session_id": session["session_id"],
            "slot": session["slots"][0],
            "beneficiaries": [ben["beneficiary_reference_id"] for ben in beneficiaries],
        }
        # post request to book appointment
        r = self.sess.post(self.SCHEDULE_APPOINTMENT_URL, json=data)
        r.raise_for_status()
        return r.json()


def filter_session(reqs: Requirements, session: dict):
    if session["available_capacity"] < 1:
        return False
    if reqs.fee_type != "ANY" and session["fee_type"] != reqs.fee_type:
        return False
    if reqs.vaccine_type != "ANY" and session["vaccine"] != reqs.vaccine_type:
        return False
    if reqs.min_age < session["min_age_limit"]:
        return False
    if session[f"available_capacity_dose{reqs.dose_seq}"] < 1:
        return False
    return True


def session_score(reqs: Requirements, session: dict) -> float:
    center_name_score = reqs.center_name_score(session["name"])
    if center_name_score > 0.2:
        return 10 * center_name_score 

    # TODO: Assign scores to sessions so that they can be sorted better
    return 0
    # if reqs.fee_type != "ANY" and session["fee_type"] != reqs.fee_type:
    #     return -float("inf")
    # if reqs.vaccine_type != "ANY" and session["vaccine"] != reqs.vaccine_type:
    #     return -float("inf")
    # if session[f"available_capacity_dose{reqs.dose_seq}"] < 1:
    #     return False
    # return True


def sort_sessions(sessions: list, reqs: Requirements):
    sessions = sorted((sess for sess in sessions if filter_session(reqs, sess)),
                      key=lambda s: session_score(reqs, s), reverse=True)
    return list(sessions)


def get_booking_date() -> str:
    DATE_FMT = "%d-%m-%Y"
    if book_date := config["booking"].get("date"):
        if book_date == "tomorrow":
            return (date.today() + timedelta(days=1)).strftime(DATE_FMT)
        assert isinstance(book_date, date)
        return book_date.strftime(DATE_FMT)
    delta = timedelta(days=0)
    if time.localtime().tm_hour > 8:
        delta = timedelta(days=1)
    return (date.today() + delta).strftime(DATE_FMT)


def booking_loop():
    reqs = Requirements(**config["requirements"])
    auth = CowinAuth(config["auth"]["mobile"])
    api = CowinApi(auth)
    pincode = config["booking"]["pincode"]
    book_date = get_booking_date()
    beneficiaries = api.get_beneficiaries()
    while True:
        sess_data = api.get_sessions_by_pincode(pincode, book_date)
        if sessions := sess_data["sessions"]:
            # TODO: Create a Session dataclass for better type checking
            if candidates := sort_sessions(sessions, reqs):
                logging.info("found candidate!", candidates[0])
                # TODO: Is captcha needed?
                # TODO: Add way for user to validate the candidate before booking
                # resp = api.book_session(candidates[0], beneficiaries, reqs)
                # logging.info("booking successful")
                # logging.debug(resp)
                break
            else:
                logging.trace(sessions)
                logging.info("Nothing good")
        else:
            logging.info("No availble")
        time.sleep(10)


def main():
    # sleep until 5:30AM if after 8PM
    if not DEBUG and time.localtime().tm_hour > 20:
        start_time = datetime.now().replace(hour=5, minute=30, second=0, microsecond=0)
        if start_time < datetime.now():
            start_time += timedelta(days=1)
        logging.info(f"Sleeping until {start_time}")
        time.sleep(start_time.timestamp() - time.time())

    server_thread = threading.Thread(target=run_app, name="web_server", daemon=True)
    server_thread.start()
    booking_loop()


if __name__ == "__main__":
    main()
