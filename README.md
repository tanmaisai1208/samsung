C:\Users\chennagiri.s\StudioProjects\Android-on-device-LLM-sample>gradlew.bat --version

------------------------------------------------------------
Gradle 8.6
------------------------------------------------------------

Build time:   2024-02-02 16:47:16 UTC
Revision:     d55c486870a0dc6f6278f53d21381396d0741c6e

Kotlin:       1.9.20
Groovy:       3.0.17
Ant:          Apache Ant(TM) version 1.10.13 compiled on January 4 2023
JVM:          21.0.10 (JetBrains s.r.o. 21.0.10+-14961533-b1163.108)
OS:           Windows 11 10.0 amd64

C:\Users\chennagiri.s\StudioProjects\Android-on-device-LLM-sample>java -version
openjdk version "21.0.10" 2026-01-20
OpenJDK Runtime Environment (build 21.0.10+-14961533-b1163.108)
OpenJDK 64-Bit Server VM (build 21.0.10+-14961533-b1163.108, mixed mode)

C:\Users\chennagiri.s\StudioProjects\Android-on-device-LLM-sample>gradlew.bat tasks

FAILURE: Build failed with an exception.

* Where:
Build file 'C:\Users\chennagiri.s\StudioProjects\Android-on-device-LLM-sample\build.gradle.kts' line: 2

* What went wrong:
Plugin [id: 'com.android.application', version: '8.4.2', apply: false] was not found in any of the following sources:

- Gradle Core Plugins (plugin is not in 'org.gradle' namespace)
- Plugin Repositories (could not resolve plugin artifact 'com.android.application:com.android.application.gradle.plugin:8.4.2')
  Searched in the following repositories:
    Google
    MavenRepo
    Gradle Central Plugin Repository

* Try:
> Run with --stacktrace option to get the stack trace.
> Run with --info or --debug option to get more log output.
> Run with --scan to get full insights.
> Get more help at https://help.gradle.org.

BUILD FAILED in 1s
