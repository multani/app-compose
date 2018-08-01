VENV = venv
PIP = $(VENV)/bin/pip

dev: $(PIP)
	$(PIP) install -e .
	ln -fs $(VENV)/bin/app-compose .

$(PIP):
	python3 -m venv venv

clean:
	rm -rf $(VENV) *.egg-info/ app-compose
