<<<<<<< HEAD
import os
import glob
from prefect import flow, task

=======
import re
from astropy.time import Time
from datetime import timedelta
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
import os

OUT_DATA_DIR = "./"
try:
    HAS_HEASOFT = True
    import heasoftpy as hsp
except ImportError:
    HAS_HEASOFT = False
    print("Warning: heasoftpy not installed. NICER L2 pipeline functionality will be disabled.")

DEFAULT_CONFIG = dict(out_data_path="./")
>>>>>>> 2ba913a (generic flags)

OUT_DATA_DIR = "./"

<<<<<<< HEAD
=======

@task(
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1000),
    task_run_name="ni_local_raw_path_{obsid}",
)
def ni_local_raw_data_path(obsid, config, **kwargs):

    return os.path.join(config["input_data_path"], obsid)


@task(
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1000),
    task_run_name="ni_remote_raw_path_{obsid}",
)
def ni_heasarc_raw_data_path(obsid, time):
    """
    Constructs the remote HEASARC FTP path for raw observation data based on OBSID and time.
    """
    date = Time(time, format="mjd").to_datetime()
    return os.path.normpath(f"/FTP/nicer/data/obs/{date.year}_{date.month:02d}/{obsid}/")


@task(
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1000),
    task_run_name="ni_base_output_{obsid}",
)
def ni_base_output_path(obsid, config):
    return os.path.join(config["out_data_path"], obsid)
>>>>>>> 2ba913a (generic flags)


@task
<<<<<<< HEAD
def process_nicer_obsid(obsid, config=None, ra="NONE", dec="NONE"):
    raise NotImplementedError("process_nicer_obsid is not yet implemented.")


@task
def ni_raw_data_path(obsid, time):
    from astropy.time import Time

    mjd = Time(time.data, format="mjd")
    mjd_dt = mjd.to_datetime()

    return os.path.normpath(f"/FTP/nicer/data/obs/{mjd_dt.year}_{mjd_dt.month:02d}//{obsid}/")


@task
def ni_base_output_path(obsid):
    return os.path.join(OUT_DATA_DIR, obsid)


@task
def ni_pipeline_output_path(obsid):
    return os.path.join(OUT_DATA_DIR, obsid + "/event_cl/")


@task
def ni_run_l2_pipeline(obsid):
    import heasoftpy as hsp

    pass
=======
def ni_pipeline_output_path(obsid, config):
    return os.path.join(config["out_data_path"], obsid + "/l2files/")


@task(
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1000),
    task_run_name="ni_pipeline_done_file_{obsid}",
)
def ni_pipeline_done_file(obsid, config):
    return os.path.join(ni_pipeline_output_path.fn(obsid, config), "PIPELINE_DONE.TXT")


@task(
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1000),
    task_run_name="nicerl2_{obsid}",
)
def ni_run_l2_pipeline(obsid, config, flags=None):

    logger = get_run_logger()
    if not HAS_HEASOFT:
        logger.error("heasoftpy not installed, cannot run NICER L2 pipeline.")
        raise ImportError("heasoftpy not installed")

    ev_dir = ni_pipeline_output_path.fn(obsid, config=config)
    full_pipe_done_file_path = os.path.join(ev_dir, "PIPELINE_DONE.TXT")

    if os.path.exists(full_pipe_done_file_path):
        logger.info(
            f"Data for {obsid} already preprocessed. Done file found at: {full_pipe_done_file_path}"
        )
        return ev_dir

    nicerl2_hsp_task = hsp.HSPTask("nicerl2")
    logger.info("Running Nicer L2 pipeline for OBSID: %s", obsid)

    datadir = ni_local_raw_data_path.fn(obsid, config=config)

    os.makedirs(ev_dir, exist_ok=True)
    logger.info(f"Ensuring desired final output directory exists: {ev_dir}")

    params = {
        "indir": datadir,
        "cldir": ev_dir,
        "clobber": True,
        "chatter": 5,
        "threshfilter": "ALL",
    }
    if flags:
        params.update(flags)

    result = nicerl2_hsp_task(**params)
    print("return code:", result.returncode)
    if result.returncode != 0:
        logger.error(f"nicerl2 failed: {result.stderr}")
        raise RuntimeError("nicerl2 failed")
    open(full_pipe_done_file_path, "a").close()

    return ev_dir


@task(
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=90),
    task_run_name="ni_barycenter_{infile}",
)
def barycenter_file(infile: str, attorb: str, ra: float, dec: float):
    logger = get_run_logger()
    logger.info(f"Barycentering {infile}")

    outfile = infile.replace(".evt", "_bary.evt")
    logger.info(f"Output file: {outfile}")

    hsp.barycorr(
        infile=infile,
        outfile=outfile,
        ra=ra,
        dec=dec,
        ephem="JPLEPH.430",
        refframe="ICRS",
        clobber="yes",
        orbitfiles=attorb,
        chatter=5,
    )

    if not os.path.exists(outfile):
        raise FileNotFoundError(f"Barycentered output file not created: {outfile}")

    return outfile


@flow(flow_run_name="ni_barycenter_{obsid}")
def barycenter_data(obsid: str, ra: float, dec: float, config: dict):
    logger = get_run_logger()
    outdir = ni_base_output_path.fn(obsid, config=config)
    logger.info(f"Barycentering NICER data in directory {outdir}")

    infile = os.path.join(outdir, "l2files", f"ni{obsid}_0mpu7_cl.evt")
    if not os.path.exists(infile):
        raise FileNotFoundError(f"Event file not found: {infile}")

    orbit_file = os.path.join(outdir, "auxil", f"ni{obsid}.orb.gz")
    if not os.path.exists(orbit_file):
        raise FileNotFoundError(f"Orbit file not found: {orbit_file}")

    return barycenter_file(infile=infile, attorb=orbit_file, ra=float(ra), dec=float(dec))


@flow
def process_nicer_obsid(obsid: str, config: dict = None, ra="NONE", dec="NONE", flags=None):
    config = DEFAULT_CONFIG if config is None else config
    logger = get_run_logger()
    logger.info(f"Processing Nicer observation {obsid}")
    base_output_dir_for_obsid = ni_base_output_path.fn(obsid, config=config)
    os.makedirs(base_output_dir_for_obsid, exist_ok=True)
    logger.info(f"Ensured base output directory exists: {base_output_dir_for_obsid}")

    ni_run_l2_pipeline(obsid, config=config, flags=flags)
    barycenter_data(obsid, ra=ra, dec=dec, config=config)
    logger.info(f"Finished processing Nicer observation {obsid}")
>>>>>>> 2ba913a (generic flags)
