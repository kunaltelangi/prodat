Frequently Asked Questions
===================================

Q: What is the role of the prodat open source tool?

A: The open source project acts as a user-controlled project manager (available as both a CLI and Python SDK) that enables users to create, run, manage, and record all aspects of their experiments.

-----

Q: Do I have to know how to use Docker to use prodat?

A: Not at all! However, knowledge of Docker will be helpful for understanding how the environments are created and setup.

------

Environment Questions
---------------------------

Q: How can I add my own environments to be used with prodat?

A: The ``environment setup`` command adds in a default environment provided by prodat in the ``prodat_environment`` directory. You can add in your own environment by modifying these files, or adding your own files to the ``prodat_environment`` directory (ie: Dockerfile, requirements.txt, package.json, etc). You can run a `prodat environment create` and use the environment ID at the time you run a task or run a workspace. You can also just directly run a task or workspace and prodat will create a new environment from ``prodat_environment`` and will set the most recent environment that was setup as the default for running tasks.

Check out our guide full guide on :ref:`bring-your-own` here.

------

Q: How does prodat handle all of my different environments?

A: The default environment that will be used for running tasks at any given time is chosen by the Dockerfile that is present in the ``prodat_environment`` directory. The other environments locally available for your project, visible with ``$ prodat environment ls`` and can be selected by passing the environment ID in as a parameter at the time of a task run or workspace creation.

-----

Q: I've made changes to the Dockerfile in my project, but the container environment isn't changing too. Why is this?

A: When running a task, prodat always looks first inside the ``prodat_environment`` directory. If an environment is not present there, it will then use a Dockerfile from the project's root directory (if present). However, after the first run, prodat creates an environment entity and Dockerfile that are replicas of the one used at the time of the initial run. Because of the priority of environment directories, prodat will utilize the Dockerfile from the ``prodat_environment`` for subsequent runs, which means that changes to the original Dockerfile outside of ``prodat_environment`` will not appear in the environment prodat has created/tracked. If you would like to change the environment, you can change it in the ``prodat_environment`` folder.

------

Q: Why does my environment have a different ID on different operating systems?

A: Environment IDs are unique hashes based on the content of the file(s). Due to differences in line separator characters on Windows and Linux/MacOS, this will cause the hashes to be different, despite the visible contents of the environment being the same. Windows utilizes ``\r\n``, while Linux/MacOS use ``\n``.