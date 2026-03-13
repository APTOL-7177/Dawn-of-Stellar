"""
UPnP 자동 포트 포워딩

miniupnpc 라이브러리를 사용하여 공유기(라우터)에 자동으로 포트를 열어줍니다.
호스트가 서버를 시작할 때 자동으로 UPnP 포트 매핑을 시도하고,
서버를 종료할 때 매핑을 제거합니다.
"""

import urllib.request
from typing import Optional, Tuple
from src.core.logger import get_logger

logger = get_logger("multiplayer.upnp")

# miniupnpc 설치 여부
_upnp_available = False
try:
    import miniupnpc
    _upnp_available = True
except ImportError:
    logger.info("miniupnpc 미설치 - UPnP 자동 포트개방 비활성화")

# 사설 IP 대역 (이중 공유기 감지용)
_PRIVATE_PREFIXES = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                     "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                     "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                     "172.30.", "172.31.", "192.168.")


def _is_private_ip(ip: str) -> bool:
    """사설 IP 여부 확인"""
    return ip.startswith(_PRIVATE_PREFIXES) or ip == "127.0.0.1"


def _fetch_public_ip() -> Optional[str]:
    """외부 서비스로 실제 공인 IP 조회 (이중 공유기 대응)"""
    services = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
    ]
    for url in services:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DawnOfStellar/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                ip = resp.read().decode().strip()
                if ip and not _is_private_ip(ip):
                    logger.info(f"공인 IP 조회 성공 ({url}): {ip}")
                    return ip
        except Exception:
            continue
    logger.warning("공인 IP 조회 실패 (모든 서비스 타임아웃)")
    return None


def is_available() -> bool:
    """UPnP 라이브러리 사용 가능 여부"""
    return _upnp_available


def try_port_mapping(internal_port: int, external_port: int = 0,
                     protocol: str = "TCP", description: str = "Dawn of Stellar") -> Tuple[bool, Optional[str], Optional[int]]:
    """
    UPnP 포트 매핑 시도

    Args:
        internal_port: 내부(로컬) 포트
        external_port: 외부 포트 (0이면 internal_port와 동일)
        protocol: 프로토콜 ("TCP" 또는 "UDP")
        description: 포트 매핑 설명

    Returns:
        (성공 여부, 외부 IP 주소, 매핑된 외부 포트)
    """
    if not _upnp_available:
        logger.warning("miniupnpc 미설치 - UPnP 포트 매핑 불가")
        return False, None, None

    if external_port == 0:
        external_port = internal_port

    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 2000  # 2초 탐색 대기

        logger.info("UPnP 게이트웨이 탐색 중...")
        devices = upnp.discover()
        if devices == 0:
            logger.warning("UPnP 게이트웨이를 찾을 수 없습니다")
            return False, None, None

        logger.info(f"UPnP 게이트웨이 {devices}개 발견")
        upnp.selectigd()

        external_ip = upnp.externalipaddress()
        logger.info(f"UPnP 외부 IP: {external_ip}")

        # 이중 공유기 감지: UPnP가 사설 IP를 반환하면 실제 공인 IP 조회
        if _is_private_ip(external_ip):
            logger.info(f"이중 공유기 감지 (UPnP IP가 사설 대역: {external_ip}), 공인 IP 조회 중...")
            public_ip = _fetch_public_ip()
            if public_ip:
                external_ip = public_ip
            else:
                logger.warning("공인 IP 조회 실패 - UPnP IP 그대로 사용")

        # 기존 매핑이 있으면 먼저 제거
        try:
            upnp.deleteportmapping(external_port, protocol)
        except Exception:
            pass  # 기존 매핑이 없으면 무시

        # 포트 매핑 추가
        # addportmapping(external_port, protocol, internal_host, internal_port, description, remote_host)
        lan_ip = upnp.lanaddr
        result = upnp.addportmapping(
            external_port, protocol, lan_ip, internal_port, description, ""
        )

        if result:
            logger.info(f"UPnP 포트 매핑 성공: {external_ip}:{external_port} -> {lan_ip}:{internal_port} ({protocol})")
            return True, external_ip, external_port
        else:
            logger.warning("UPnP 포트 매핑 실패 (라우터가 거부)")
            return False, external_ip, None

    except Exception as e:
        logger.warning(f"UPnP 포트 매핑 오류: {e}")
        return False, None, None


def remove_port_mapping(external_port: int, protocol: str = "TCP") -> bool:
    """
    UPnP 포트 매핑 제거

    Args:
        external_port: 외부 포트
        protocol: 프로토콜

    Returns:
        성공 여부
    """
    if not _upnp_available:
        return False

    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 2000
        devices = upnp.discover()
        if devices == 0:
            return False

        upnp.selectigd()
        upnp.deleteportmapping(external_port, protocol)
        logger.info(f"UPnP 포트 매핑 제거: 포트 {external_port} ({protocol})")
        return True

    except Exception as e:
        logger.warning(f"UPnP 포트 매핑 제거 오류: {e}")
        return False


def get_external_ip() -> Optional[str]:
    """
    실제 공인 IP 주소 가져오기 (UPnP → 사설이면 외부 서비스 폴백)

    Returns:
        공인 IP 주소 또는 None
    """
    # 1차: UPnP로 시도
    if _upnp_available:
        try:
            upnp = miniupnpc.UPnP()
            upnp.discoverdelay = 2000
            if upnp.discover() > 0:
                upnp.selectigd()
                ip = upnp.externalipaddress()
                if ip and not _is_private_ip(ip):
                    return ip
        except Exception:
            pass

    # 2차: 외부 서비스로 폴백
    return _fetch_public_ip()
