> Task :app:compileDebugKotlin FAILED
Execution failed for task ':app:compileDebugKotlin'.
> Could not resolve all files for configuration ':app:kotlin-extension'.
   > Could not resolve androidx.compose.compiler:compiler:1.5.14.
     Required by:
         project :app
      > Could not resolve androidx.compose.compiler:compiler:1.5.14.
         > Could not get resource 'https://dl.google.com/dl/android/maven2/androidx/compose/compiler/compiler/1.5.14/compiler-1.5.14.pom'.
            > Could not GET 'https://dl.google.com/dl/android/maven2/androidx/compose/compiler/compiler/1.5.14/compiler-1.5.14.pom'.
               > Got SSL handshake exception during request. It might be caused by SSL misconfiguration
                  > (certificate_unknown) PKIX path building failed: sun.security.provider.certpath.SunCertPathBuilderException: unable to find valid certification path to requested target
      > Could not resolve androidx.compose.compiler:compiler:1.5.14.
         > Could not get resource 'https://repo.maven.apache.org/maven2/androidx/compose/compiler/compiler/1.5.14/compiler-1.5.14.pom'.
            > Could not GET 'https://repo.maven.apache.org/maven2/androidx/compose/compiler/compiler/1.5.14/compiler-1.5.14.pom'.
               > Got SSL handshake exception during request. It might be caused by SSL misconfiguration
                  > (certificate_unknown) PKIX path building failed: sun.security.provider.certpath.SunCertPathBuilderException: unable to find valid certification path to requested target

* Try:
> Run with --stacktrace option to get the stack trace.
> Run with --info or --debug option to get more log output.
> Run with --scan to get full insights.
> Get more help at https://help.gradle.org.
Fix with AI

