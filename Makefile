PYTHON ?= python3
TOOLS_DIR ?= /home/daizhiyuan/workspace/tmpdir/simproxy-tools

.PHONY: help test lint fmt install bootstrap drclient validate-simpoint benchmark-simpoint clean

BBV ?= phase_sample.bbv
K ?= 3
CASES ?= 20

help:
	@echo "targets: install test lint fmt bootstrap drclient validate-simpoint benchmark-simpoint clean"
	@echo "  validate-simpoint BBV=... K=... SIMPOINT_BIN=..."
	@echo "  benchmark-simpoint CASES=... SIMPOINT_BIN=..."

install:
	$(PYTHON) -m pip install -e '.[dev]'

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check python tests

fmt:
	$(PYTHON) -m ruff format python tests

bootstrap:
	SIMPROXY_TOOLS_DIR=$(TOOLS_DIR) ./scripts/bootstrap_toolchain.sh

drclient:
	cmake -S . -B build -G Ninja \
		-DCMAKE_SYSTEM_NAME=Linux \
		-DCMAKE_SYSTEM_PROCESSOR=aarch64 \
		-DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc \
		-DDynamoRIO_DIR=$(TOOLS_DIR)/DynamoRIO-AArch64-Linux-11.91.20756/cmake
	cmake --build build

validate-simpoint:
	$(PYTHON) scripts/validate_simpoint.py $(BBV) --k $(K) --strict

benchmark-simpoint:
	$(PYTHON) scripts/benchmark_simpoint.py --cases $(CASES)

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
