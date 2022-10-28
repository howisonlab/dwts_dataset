# FROM quay.io/2i2c/utexas-image:latest 
FROM jupyter/datascience-notebook:latest

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mamba install --yes \
    'r-littler' && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"  
