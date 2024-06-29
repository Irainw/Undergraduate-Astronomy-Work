
# Read in Standard Solar Model (SSM) from Bahcall et al. (2006).

using PyPlot,DelimitedFiles,Statistics

if !@isdefined(CGS)
  include("CGS.jl")
  using Main.CGS
end

include("exportenergy.jl")

#data = readdlm("bs05_agsop.dat.txt",comment_char='#',comments=true)
data = readdlm("bp2000_ssm.txt",comment_char='#',comments=true)

m = data[:,1]
r = data[:,2] 
t = data[:,3]
rho = data[:,4]
p = data[:,5]
lum = data[:,6]
x1 = data[:,7]
x4 = data[:,8]
x3 = data[:,9]
x12 = data[:,10]
x14 = data[:,11]
x16 = data[:,12]
nr = length(r)
xtot = zeros(nr)
for i=1:nr
  xtot[i] = sum(data[i,7:end])
end

# Some basic plots:

clf()
plot(r,m)
xlabel(L"$R/R_\odot$")
ylabel(L"$M/M_\odot$")
tight_layout()
savefig("BPB2000_R_M.png",bbox_inches="tight")
read(stdin,Char)
clf()

plot(r,rho)
xlabel(L"$R/R_\odot$")
ylabel(L"$\rho$ [g/cm$^2$]")
tight_layout()
savefig("BPB2000_R_rho.png",bbox_inches="tight")
read(stdin,Char)
clf()

plot(r,x1,label="H")
legend()
axis([0,1,0,1.1])
tight_layout()
read(stdin,Char)
plot(r,x4,label="He")
legend()
tight_layout()
read(stdin,Char)
plot(r,1 .-x1 .- x4,label="Everything else")
xlabel(L"$R/R_\odot$")
ylabel(L"X,Y,1-X-Y")
tight_layout()
legend()
savefig("BPB2000_R_XY.png",bbox_inches="tight")
read(stdin,Char)
clf()

semilogy(r,p)
xlabel(L"$R/R_\odot$")
ylabel(L"$P$ [dyne/cm$^2$]")
tight_layout()
savefig("BPB2000_R_P.png",bbox_inches="tight")
read(stdin,Char)
clf()

plot(r,lum)
xlabel(L"$R/R_\odot$")
ylabel(L"$L/L_\odot$")
tight_layout()
savefig("BPB2000_R_L.png",bbox_inches="tight")
read(stdin,Char)
clf()

semilogy(r,t)
xlabel(L"$R/R_\odot$")
ylabel(L"$T$ [K]")
tight_layout()
savefig("BPB2000_R_T.png",bbox_inches="tight")
read(stdin,Char)
clf()

# Compute the hydrostatic equilibrium equation:

dpdr_fun(p1,p2,r1,r2) = (p2-p1)/(r2-r1)/RSUN

dpdr = zeros(nr)
for i=1:nr
  if i == 1
    dpdr[i] = dpdr_fun(p[1],p[10],0.0,r[10])
  elseif i == nr
    dpdr[i] = dpdr_fun(p[end],0.0,r[end],1.0)
  else
    i0 = minimum([3,i-1,nr-i])
    dpdr[i] = dpdr_fun(p[i-i0],p[i+i0],r[i-i0],r[i+i0])
  end
end
#dpdr = dpdr_fun.([p[1];p[1:end-1]],[p[2:end];0.0],[0.0;r[1:end-1]],[r[2:end];1.0])

# Now, compute gravitational acceleration times density:

acc_rho_fun(m,r,rho) = -GRAV*MSUN*m*rho/(r*RSUN)^2

acc_rho = acc_rho_fun.(m,r,rho)

# Now, compare these:

clf()
plot(r,dpdr,label=L"$dP/dr$ [cgs]")
xlabel(L"$r/R_\odot$")
ylabel("Various [dyne/sq cm]")
legend()
read(stdin,Char)
plot(r,acc_rho,label=L"$-GM\rho/r^2$ [cgs]")
legend()
read(stdin,Char)
plot(r,dpdr-acc_rho,label="Difference")
legend()
tight_layout()
savefig("BPB2000_R_dPdr.png",bbox_inches="tight")
read(stdin,Char)

# Now, show mass conservation:

clf()

dmdr_fun(m1,m2,r1,r2) = (m2-m1)*MSUN/(r2-r1)/RSUN

dmdr = zeros(nr)
for i=1:nr
  if i == 1
    dmdr[i] = dmdr_fun(0.0,m[10],0.0,r[10])
  elseif i == nr
    dmdr[i] = dmdr_fun(m[end],1.0,r[end],1.0)
  else
    i0 = minimum([3,i-1,nr-i])
    dmdr[i] = dmdr_fun(m[i-i0],m[i+i0],r[i-i0],r[i+i0])
  end
end

# Now, compute the mass in a shell per unit radius:

fpir2rho_fun(r,rho) = 4*pi*(r*RSUN)^2*rho

fpir2rho = fpir2rho_fun.(r,rho)

plot(r,dmdr,label=L"$dm/dr$ [cgs]")
xlabel(L"$r/R_\odot$")
ylabel("Various [g/cm]")
legend()
read(stdin,Char)
plot(r,fpir2rho,label=L"$4\pi r^2\rho$ [cgs]")
xlabel(L"$r/R_\odot$")
ylabel("Various [g/cm]")
legend()
read(stdin,Char)
plot(r,dmdr - fpir2rho,label="Difference")
xlabel(L"$r/R_\odot$")
ylabel("Various [g/cm]")
legend()
tight_layout()
savefig("BPB2000_R_dMdr.png",bbox_inches="tight")
read(stdin,Char)

# Next, compute the Virial theorem:

Eint(p,r,rho,dr) = 1.5*p*4*pi*r^2*dr*RSUN^3
dr = zeros(nr)
for i=2:nr-1
  dr[i] = 0.5*(r[i+1] - r[i-1])
end
dr[1] = r[1]+0.5*(r[2]-r[1])
dr[end] = 1.0-0.5*(r[end]+r[end-1])

Egr(m,r,dm) = -GRAV*m/r*dm*MSUN^2/RSUN

dm = zeros(nr)
for i=2:nr-1
  dm[i] = 0.5*(m[i+1] - m[i-1])
end
dm[1] = m[1]+0.5*(m[2]-m[1])
dm[end] = 1.0-0.5*(m[end]+m[end-1])

clf()
plot(r,cumsum(Eint.(p,r,rho,dr)),label=L"$E_{int}$")
plot(r,0.0 .* r,linestyle=":")
xlabel(L"$r/R_\odot$")
ylabel(L"$Energy [erg]$")
legend()
read(stdin,Char)
plot(r,cumsum(Egr.(m,r,dm)),label=L"$E_{gr}$")
legend()
read(stdin,Char)
plot(r,cumsum(Eint.(p,r,rho,dr)) .+ 0.5 .* cumsum(Egr.(m,r,dm)),label=L"$E_{int}+\frac{1}{2}E_{gr} $")
legend()
read(stdin,Char)
plot(r,cumsum(Eint.(p,r,rho,dr)) .+ cumsum(Egr.(m,r,dm)),label=L"$E_{int}+E_{gr} $")
legend()
tight_layout()
savefig("BPB2000_R_Virial.png",bbox_inches="tight")

read(stdin,Char)

# Now, compute energy generation:

clf()
#LSUN = STEFANBOLTZMANN*4*pi*RSUN^2*TSUN^4
LSUN = 3.8515e33

dldr_fun(l1,l2,r1,r2) = (l2-l1)*LSUN/(r2-r1)/RSUN

dldr = zeros(nr)
for i=1:nr
  if i == 1
    dldr[i] = dldr_fun(0.0,lum[10],0.0,r[10])
  elseif i == nr
    dldr[i] = dldr_fun(lum[end],1.0,r[end],1.0)
  else
    i0 = minimum([1,i-1,nr-i])
    dldr[i] = dldr_fun(lum[i-i0],lum[i+i0],r[i-i0],r[i+i0])
  end
end

# Now, compute the energy generation rate:

#nuc_cno(rho,x1,x14,t) = 1e28*rho*x1*x14/(t/1e6)^(2//3)*exp(-152.313/(t/1e6)^(1//3))
#nuc_pp(x1,rho,t) = 3.1e6*x1^2*rho/(t/1e6)^(2//3)*exp(-33.81/(t/1e6)^(1//3))
nuc_pp(x1,rho,t) = 0.11*x1^2*rho*(t/1e7)^4

#nuc_rate_fun(r,rho,x1,x14,t) = 4*pi*(r*RSUN)^2*(nuc_pp(x1,rho,t) + nuc_cno(rho,x1,x14,t))*rho
nuc_rate_fun(r,rho,x1,x14,t) = 4*pi*(r*RSUN)^2*(nuc_pp(x1,rho,t) )*rho

nuc_rate = nuc_rate_fun.(r,rho,x1,x14,t)

plot(r,dldr,label=L"$dL/dr$ [cgs]")
xlabel(L"$r/R_\odot$")
ylabel("Various [erg/sec/cm]")
legend()
read(stdin,Char)
#plot(r,nuc_rate,label=L"$4\pi r^2\epsilon$ [cgs]")
#xlabel(L"$r/R_\odot$")
#ylabel("Various [erg/sec/cm]")
#legend()
#read(stdin,Char)
#plot(r,dldr - nuc_rate,label="Difference")
xlabel(L"$r/R_\odot$")
ylabel("Various [erg/sec/cm]")

#
#loglog(t,dldr ./ (4pi .* (r*RSUN).^2) ./ (x1 .* rho).^2)
#plot(t,nuc_pp.(1.0,1.0,t))
#plot(t,nuc_cno.(1.0,1.0,x14 .* x1,t))
#
#axis([5e6,2e7,1e-2,2])
#
#clf()
#loglog(t,dldr ./ (4pi .* (r*RSUN).^2))
##plot(t,nuc_pp.(x1,rho,t).*rho)
#axis([5e6,2e7,1e-2,1e4])
##plot(t,nuc_cno.(rho,x1,x14,t) .* rho)
#
nuc_rate = zeros(nr)
for i=1:nr
  #nuc_rate[i] = energy(DL,TL,X,Y,XHE3,XC12,XC13,XN14,XO16,XO18,IU)
  nuc_rate[i] = energy(log10(rho[i]),log10(t[i]),x1[i],x4[i],x3[i],x12[i],0.0,x14[i],x16[i],0.0,1) *1.1
#  println(i," ",rho[i]," ",t[i]," ",nuc_rate[i])
end

plot(r,nuc_rate .* rho .* (4pi*RSUN^2) .* r.^2,label="exportenergy")
legend()
read(stdin,Char)
plot(r,dldr - nuc_rate .* rho .* (4pi*RSUN^2) .* r.^2,label="Difference")
legend()
tight_layout()
savefig("BPB2000_R_dLdr.png",bbox_inches="tight")

read(stdin,Char)
clf()
loglog(t,dldr ./ (4pi .* (r*RSUN).^2),label="dL/dr")
legend()
ylabel(L"Various [erg/sec/cm$^3$/gm]")
axis([5e6,2e7,1e-1,1e5])
read(stdin,Char)
plot(t,nuc_rate .* rho,label="exportenergy")
axis([5e6,2e7,1e-1,1e5])
legend()
xlabel(L"$r/R_\odot$")
ylabel(L"Various [erg/sec/cm$^3$/gm]")
axis([5e6,2e7,1e-1,1e5])
tight_layout()
