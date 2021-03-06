#!/usr/bin/env python3
"""Defines base classes for application providers.

Defines the class interfaces for implementation that fetches
informations about runnable apps. This could be Steam, 
Emulators, local .desktop entries or the application menu.

Each implementation must implement at least AppProvider
"""

from subprocess import Popen
from  psutil import Process, NoSuchProcess, STATUS_DEAD, wait_procs
import logging
LOGGER = logging.getLogger(__name__)

# Load platform dependent utils
import platform
system = platform.system()
if system == 'Linux':
	LOGGER.info('Detected Linux system')
	from .platform import linux as gameplay_sys
elif system == 'Darwin':
	LOGGER.info('Detected Darwin system')
	from .platform import darwin as gameplay_sys
elif system == 'Windows':
	LOGGER.info('Detected Windows system')
	from .platform import windows as gameplay_sys
else:
	# Try with linux as fallback...
	LOGGER.info('Detected unknown system, using Linux API')
	from .platform import linux as gameplay_sys

class AppProcess:
	def __init__(self, appid, process):
		if process is not Process:
			process = Process(process.pid)
		self.appid = appid
		self.process = process
		self.pid = process.pid
		self._suspended = False
		self._window = None

	def is_running(self):
		try:
			return self.process.is_running()
		except:
			return False
	
	def status(self):
		try:
			return self.process.status()
		except:
			return STATUS_DEAD
	
	def is_suspended(self):
		return self._suspended and self.is_running()
	
	def terminate(self):
		"""Terminates the current process and all of the subprocesses.
		If termination fails this method call falls back to kill().
	
		A suspended process will be waked before termination.
		"""
		try:
			if self.is_suspended():
				procs = self.process.children(recursive=True)
				procs.append(self.process)
				for p in procs:
					LOGGER.info('Resuming child process %d before termination' % p.pid)
					p.resume()
				
			if self.is_running():
				procs = self.process.children(recursive=True)
				procs.append(self.process)
				for p in procs:
					LOGGER.info('Terminating child process %d' % p.pid)
					p.terminate()
				gone, still_alive = wait_procs(procs, timeout=3, callback=self._on_terminate)
				for p in still_alive:
					LOGGER.info('Killing child process %d' % p.pid)
					p.kill()
			else:
				LOGGER.info('Process ' + self.process.pid + ' is not active anymore.')
		except:
			LOGGER.exception('Failed to kill process %d' % self.process.pid)

	def suspend(self):
		""" Suspends the current process and tries to retrieve
		the applications window name.
		"""
		try:
			if self.is_running():
				if not self._suspended:
					self._window = gameplay_sys.get_foreground_window()
					procs = self.process.children(recursive=True)
					procs.append(self.process)
					for p in procs:
						LOGGER.info('Suspending child process %d' % p.pid)
						p.suspend()
					self._suspended = True
			else:
				LOGGER.info('Process ' + self.process.pid + ' is not active anymore.')
			
		except:
			LOGGER.exception('Failed to suspend process %d' % self.process.pid)
	
	def resume(self, raiseCallback = None):
		""" Resume the current process and tries to put the applications window into foreground.
		If the window is not available the 'raiseCallback' is executed.
		"""
		try:
			if self.is_suspended():
				self._suspended = False
				procs = self.process.children(recursive=True)
				procs.append(self.process)
				for p in procs:
					LOGGER.info('Resuming child process %d' % p.pid)
					p.resume()
				if self._window is not None:
					try:
						gameplay_sys.set_foreground_window(self._window)
					except:
						LOGGER.exception('Failed to activate process window')
						if raiseCallback is not None:
							raiseCallback()
				else:
					if raiseCallback is not None:
						raiseCallback()
			else:
				LOGGER.info('Process ' + self.process.pid + ' is not suspended anymore.')
			
		except:
			LOGGER.exception('Failed to resume process %d' % self.process.pid)

	def _on_terminate(self, proc):
		LOGGER.info("Child process process {} terminated with exit code {}".format(proc.pid, proc.returncode))

class AppItem:
	def __init__(self, id, label, icon = None, icon_selected = None, suspended = False, cmd=None, categories=[]):
		self.id = id
		self.label = label
		self.icon = icon
		self.icon_selected = icon_selected
		self.suspended = suspended
		self.cmd = cmd
		self.categories = categories

	def execute(self):
		""" Executes the application and returns a AppProcess object,
		False if the command fails to run and None if the
		AppItem is not executable.
		"""
		if self.cmd is not None:
			LOGGER.info('Executing command "%s"' % ' '.join(self.cmd))
			return AppProcess(self.id, Popen(self.cmd))
		return None

class AppProvider:
	def __init__(self, settings):
		self.settings = settings

	def get_apps(self):
		""" Returns a list of AppItem objects """
		return []

#  vim: set fenc=utf-8 ts=4 sw=4 noet :

